import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from auction.constants import (
    AUCTION_STATUS_SOLD,
    AUCTION_STATUS_UNPAID,
    EVENT_TYPE_PAYMENT_FAILED,
    EVENT_TYPE_PAYMENT_SUCCEEDED,
)
from auction.repository.auction_repository import apply_payment_result_if_pending
from auction.repository.payment_status_repository import record_event_id


async def apply_payment_result(
    session: AsyncSession,
    event_id: uuid.UUID,
    auction_id: uuid.UUID,
    event_type: str,
) -> None:
    inserted = await record_event_id(session, event_id)
    if not inserted:
        return
    if event_type == EVENT_TYPE_PAYMENT_SUCCEEDED:
        status = AUCTION_STATUS_SOLD
    elif event_type == EVENT_TYPE_PAYMENT_FAILED:
        status = AUCTION_STATUS_UNPAID
    else:
        raise ValueError(f"unsupported event type {event_type}")
    await apply_payment_result_if_pending(session, auction_id, status)
