import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from settlement.entity.processed_event_entity import ProcessedEvent


async def record_event_id(session: AsyncSession, event_id: uuid.UUID) -> bool:
    stmt = (
        insert(ProcessedEvent)
        .values(event_id=event_id)
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = await session.execute(stmt)
    return result.rowcount > 0
