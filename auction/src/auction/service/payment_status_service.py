import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from auction.repository.payment_status_repository import (
    get_payment_ready,
    record_event_id,
    upsert_if_newer_version,
)


async def apply_payment_status(
    session: AsyncSession,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    payment_ready: bool,
    version: int,
) -> None:
    inserted = await record_event_id(session, event_id)
    if not inserted:
        return
    await upsert_if_newer_version(session, user_id, payment_ready, version)


async def is_payment_ready(session: AsyncSession, user_id: uuid.UUID) -> bool:
    return await get_payment_ready(session, user_id)
