from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from stripe import SignatureVerificationError, Webhook

from settlement.config import settings
from settlement.repository import record_stripe_event, stripe_event_exists
from settlement.service.payment_method_service import persist_attached_payment_method
from settlement.service.payment_result_service import apply_payment_intent_result


def verify_stripe_event(payload: bytes, signature: str | None) -> object:
    if signature is None:
        raise SignatureVerificationError("missing signature", "")
    return Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)


async def handle_stripe_webhook(
    session: AsyncSession, payload: bytes, signature: str | None
) -> None:
    event: Any = verify_stripe_event(payload, signature)
    event_id = str(event["id"])
    if await stripe_event_exists(session, event_id):
        return
    event_type = str(event["type"])
    data_object = event["data"]["object"]
    if event_type == "payment_method.attached":
        customer_id = data_object["customer"]
        payment_method_id = data_object["id"]
        if isinstance(customer_id, str) and isinstance(payment_method_id, str):
            await persist_attached_payment_method(
                session, customer_id, payment_method_id
            )
        await record_stripe_event(session, event_id)
        return
    if event_type == "setup_intent.succeeded":
        customer_id = data_object["customer"]
        payment_method_id = data_object["payment_method"]
        if isinstance(customer_id, str) and isinstance(payment_method_id, str):
            await persist_attached_payment_method(
                session, customer_id, payment_method_id
            )
        await record_stripe_event(session, event_id)
        return
    payment_intent_id = data_object["id"]
    if isinstance(payment_intent_id, str):
        await apply_payment_intent_result(session, event_type, payment_intent_id)
    await record_stripe_event(session, event_id)
