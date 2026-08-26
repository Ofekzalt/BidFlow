import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from auction.entity import BidderPaymentStatus, ProcessedEvent


async def record_event_id(session: AsyncSession, event_id: uuid.UUID) -> bool:
    stmt = (
        insert(ProcessedEvent)
        .values(event_id=event_id)
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


async def upsert_if_newer_version(
    session: AsyncSession,
    user_id: uuid.UUID,
    payment_ready: bool,
    version: int,
) -> None:
    table = BidderPaymentStatus.__table__
    stmt = insert(table).values(
        user_id=user_id,
        payment_ready=payment_ready,
        version=version,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[table.c.user_id],
        set_={
            "payment_ready": stmt.excluded.payment_ready,
            "version": stmt.excluded.version,
            "updated_at": func.now(),
        },
        where=table.c.version < stmt.excluded.version,
    )
    await session.execute(stmt)


async def get_payment_ready(session: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(BidderPaymentStatus.payment_ready).where(
            BidderPaymentStatus.user_id == user_id
        )
    )
    value = result.scalar_one_or_none()
    return bool(value)
