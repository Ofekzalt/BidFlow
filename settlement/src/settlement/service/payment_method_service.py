import asyncio
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import InvalidRequestError

from settlement.config.stripe_client import create_stripe_client
from settlement.constants import (
    EVENT_TYPE_PAYMENT_METHOD_READY,
    EVENT_TYPE_PAYMENT_METHOD_REMOVED,
    EVENT_VERSION_V1,
)
from settlement.dto import PaymentMethodResponse
from settlement.entity.outbox_event_entity import OutboxEvent
from settlement.repository import (
    clear_defaults_for_user,
    create_payment_method,
    delete_payment_method,
    get_by_id,
    get_by_stripe_customer_id,
    get_by_stripe_payment_method_id,
    insert_outbox,
    list_by_user,
)


async def next_payment_method_version(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.execute(
        select(OutboxEvent.payload).where(
            OutboxEvent.aggregate_id == user_id,
            OutboxEvent.event_type.in_(
                (EVENT_TYPE_PAYMENT_METHOD_READY, EVENT_TYPE_PAYMENT_METHOD_REMOVED)
            ),
        )
    )
    versions = [int(row[0]["version"]) for row in result.all()]
    return max(versions, default=0) + 1


async def emit_payment_method_event(
    session: AsyncSession, user_id: uuid.UUID, event_type: str
) -> None:
    version = await next_payment_method_version(session, user_id)
    await insert_outbox(
        session,
        event_type,
        EVENT_VERSION_V1,
        user_id,
        {"user_id": str(user_id), "version": version},
    )


async def persist_attached_payment_method(
    session: AsyncSession, stripe_customer_id: str, stripe_payment_method_id: str
) -> None:
    existing = await get_by_stripe_payment_method_id(session, stripe_payment_method_id)
    if existing is not None:
        return
    customer = await get_by_stripe_customer_id(
        session, stripe_customer_id, for_update=True
    )
    if customer is None:
        return
    await clear_defaults_for_user(session, customer.user_id)
    await create_payment_method(
        session,
        customer.user_id,
        stripe_payment_method_id,
        is_default=True,
    )
    await emit_payment_method_event(
        session, customer.user_id, EVENT_TYPE_PAYMENT_METHOD_READY
    )


async def list_payment_methods(
    session: AsyncSession, user_id: uuid.UUID
) -> list[PaymentMethodResponse]:
    methods = await list_by_user(session, user_id)
    return [
        PaymentMethodResponse(
            id=method.id,
            stripe_payment_method_id=method.stripe_payment_method_id,
            is_default=method.is_default,
        )
        for method in methods
    ]


async def remove_payment_method(
    session: AsyncSession, user_id: uuid.UUID, method_id: uuid.UUID
) -> None:
    method = await get_by_id(session, method_id)
    if method is None or method.user_id != user_id:
        raise HTTPException(status_code=404)
    stripe_payment_method_id = method.stripe_payment_method_id
    await delete_payment_method(session, method)
    remaining = await list_by_user(session, user_id)
    if not remaining:
        await emit_payment_method_event(
            session, user_id, EVENT_TYPE_PAYMENT_METHOD_REMOVED
        )
    client = create_stripe_client()
    try:
        await asyncio.to_thread(
            client.v1.payment_methods.detach, stripe_payment_method_id
        )
    except InvalidRequestError:
        return
