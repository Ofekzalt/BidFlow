import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from settlement.constants import (
    EVENT_TYPE_PAYMENT_FAILED,
    EVENT_TYPE_PAYMENT_SUCCEEDED,
)
from settlement.entity.outbox_event_entity import OutboxEvent


async def insert_outbox(
    session: AsyncSession,
    event_type: str,
    event_version: str,
    aggregate_id: uuid.UUID,
    payload: dict[str, Any],
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        event_version=event_version,
        aggregate_id=aggregate_id,
        payload=payload,
    )
    session.add(event)
    await session.flush()
    return event


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


async def has_payment_result_outbox(
    session: AsyncSession, auction_id: uuid.UUID
) -> bool:
    result = await session.execute(
        select(OutboxEvent.id).where(
            OutboxEvent.aggregate_id == auction_id,
            OutboxEvent.event_type.in_(
                (EVENT_TYPE_PAYMENT_SUCCEEDED, EVENT_TYPE_PAYMENT_FAILED)
            ),
        )
    )
    return result.first() is not None
