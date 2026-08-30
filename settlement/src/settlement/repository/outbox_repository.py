from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from settlement.entity.outbox_event_entity import OutboxEvent


async def claim_unpublished(session: AsyncSession, limit: int) -> list[OutboxEvent]:
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    return list[OutboxEvent](result.scalars().all())


async def mark_published(event: OutboxEvent) -> None:
    event.published_at = datetime.now(UTC)
