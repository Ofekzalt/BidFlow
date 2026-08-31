import asyncio
import uuid

from settlement.config import SessionLocal
from settlement.config.stripe_client import create_stripe_client
from settlement.constants import (
    EVENT_TYPE_PAYMENT_FAILED,
    EVENT_VERSION_V1,
    PAYMENT_IDEMPOTENCY_PREFIX,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_REQUIRES_ACTION,
    PAYMENT_STATUS_SUCCEEDED,
)
from settlement.repository import (
    get_by_auction_id,
    get_by_user_id,
    get_default_by_user,
    has_payment_result_outbox,
    insert_notification,
    insert_outbox,
    insert_payment,
    record_event_id,
)


def payment_status_from_intent(stripe_status: str) -> str:
    if stripe_status == "succeeded":
        return PAYMENT_STATUS_SUCCEEDED
    if stripe_status in {"requires_action", "requires_source_action"}:
        return PAYMENT_STATUS_REQUIRES_ACTION
    if stripe_status in {
        "processing",
        "requires_confirmation",
        "requires_capture",
    }:
        return PAYMENT_STATUS_PENDING
    return PAYMENT_STATUS_FAILED


async def process_auction_ended(
    event_id: uuid.UUID,
    auction_id: uuid.UUID,
    winner_id: uuid.UUID,
    amount_cents: int,
    currency: str,
) -> None:
    async with SessionLocal() as session:
        await record_event_id(session, event_id)
        await insert_payment(session, auction_id, winner_id, amount_cents, currency)
        await session.commit()

    stripe_customer_id: str | None = None
    stripe_payment_method_id: str | None = None
    async with SessionLocal() as session:
        payment = await get_by_auction_id(session, auction_id, for_update=True)
        if payment is None or payment.status != PAYMENT_STATUS_PENDING:
            return
        method = await get_default_by_user(session, winner_id)
        customer = await get_by_user_id(session, winner_id)
        if method is None or customer is None:
            if await has_payment_result_outbox(session, auction_id):
                await session.commit()
                return
            payment.status = PAYMENT_STATUS_FAILED
            payload = {"auction_id": str(auction_id)}
            await insert_outbox(
                session,
                EVENT_TYPE_PAYMENT_FAILED,
                EVENT_VERSION_V1,
                auction_id,
                payload,
            )
            await insert_notification(
                session, winner_id, EVENT_TYPE_PAYMENT_FAILED, payload
            )
            await session.commit()
            return
        stripe_customer_id = customer.stripe_customer_id
        stripe_payment_method_id = method.stripe_payment_method_id
        await session.commit()

    client = create_stripe_client()
    intent = await asyncio.to_thread(
        client.v1.payment_intents.create,
        params={
            "amount": amount_cents,
            "currency": currency.lower(),
            "customer": stripe_customer_id,
            "payment_method": stripe_payment_method_id,
            "confirm": True,
            "off_session": True,
            "automatic_payment_methods": {
                "enabled": True,
                "allow_redirects": "never",
            },
        },
        options={
            "idempotency_key": f"{PAYMENT_IDEMPOTENCY_PREFIX}{auction_id}",
        },
    )
    async with SessionLocal() as session:
        payment = await get_by_auction_id(session, auction_id, for_update=True)
        if payment is None or payment.status != PAYMENT_STATUS_PENDING:
            return
        payment.stripe_payment_intent_id = intent.id
        await session.commit()
    async with SessionLocal() as session:
        payment = await get_by_auction_id(session, auction_id, for_update=True)
        if payment is None or payment.status != PAYMENT_STATUS_PENDING:
            return
        if payment.stripe_payment_intent_id is None:
            payment.stripe_payment_intent_id = intent.id
        payment.status = payment_status_from_intent(str(intent.status))
        await session.commit()
