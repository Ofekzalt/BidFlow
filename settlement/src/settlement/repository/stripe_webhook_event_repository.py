from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from settlement.entity import StripeWebhookEvent


async def stripe_event_exists(session: AsyncSession, stripe_event_id: str) -> bool:
    result = await session.execute(
        select(StripeWebhookEvent.stripe_event_id).where(
            StripeWebhookEvent.stripe_event_id == stripe_event_id
        )
    )
    return result.scalar_one_or_none() is not None


async def record_stripe_event(session: AsyncSession, stripe_event_id: str) -> bool:
    stmt = (
        insert(StripeWebhookEvent)
        .values(stripe_event_id=stripe_event_id)
        .on_conflict_do_nothing(index_elements=["stripe_event_id"])
    )
    result = await session.execute(stmt)
    return result.rowcount > 0
