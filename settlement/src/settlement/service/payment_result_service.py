from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from settlement.constants import (
    EVENT_TYPE_PAYMENT_FAILED,
    EVENT_TYPE_PAYMENT_SUCCEEDED,
    EVENT_VERSION_V1,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_REQUIRES_ACTION,
    PAYMENT_STATUS_SUCCEEDED,
)
from settlement.dto import NotificationResponse
from settlement.repository import (
    get_by_stripe_payment_intent_id,
    has_payment_result_outbox,
    insert_notification,
    insert_outbox,
    list_notifications,
)

PAYMENT_INTENT_RESULTS = {
    "payment_intent.succeeded": (
        PAYMENT_STATUS_SUCCEEDED,
        EVENT_TYPE_PAYMENT_SUCCEEDED,
    ),
    "payment_intent.payment_failed": (
        PAYMENT_STATUS_FAILED,
        EVENT_TYPE_PAYMENT_FAILED,
    ),
    "payment_intent.requires_action": (
        PAYMENT_STATUS_REQUIRES_ACTION,
        EVENT_TYPE_PAYMENT_FAILED,
    ),
}


class PaymentIntentNotReadyError(Exception):
    pass


async def apply_payment_intent_result(
    session: AsyncSession, event_type: str, payment_intent_id: str
) -> None:
    mapping = PAYMENT_INTENT_RESULTS.get(event_type)
    if mapping is None:
        return
    status, outbox_type = mapping
    payment = await get_by_stripe_payment_intent_id(
        session, payment_intent_id, for_update=True
    )
    if payment is None:
        raise PaymentIntentNotReadyError
    if await has_payment_result_outbox(session, payment.auction_id):
        return
    payment.status = status
    payload = {"auction_id": str(payment.auction_id)}
    await insert_outbox(
        session,
        outbox_type,
        EVENT_VERSION_V1,
        payment.auction_id,
        payload,
    )
    await insert_notification(session, payment.winner_id, outbox_type, payload)


async def list_user_notifications(
    session: AsyncSession, user_id: UUID
) -> list[NotificationResponse]:
    notifications = await list_notifications(session, user_id)
    return [
        NotificationResponse(
            id=item.id,
            type=item.type,
            payload=item.payload,
            created_at=item.created_at,
        )
        for item in notifications
    ]
