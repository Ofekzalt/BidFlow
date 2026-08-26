import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from auction.entity.outbox_event_entity import OutboxEvent


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
