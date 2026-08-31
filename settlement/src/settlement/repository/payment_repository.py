import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from settlement.constants import PAYMENT_STATUS_PENDING
from settlement.entity import Payment


async def insert_payment(
    session: AsyncSession,
    auction_id: uuid.UUID,
    winner_id: uuid.UUID,
    amount_cents: int,
    currency: str,
) -> bool:
    stmt = (
        insert(Payment)
        .values(
            id=uuid.uuid4(),
            auction_id=auction_id,
            winner_id=winner_id,
            amount_cents=amount_cents,
            currency=currency,
            status=PAYMENT_STATUS_PENDING,
        )
        .on_conflict_do_nothing(index_elements=["auction_id"])
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


async def get_by_auction_id(
    session: AsyncSession,
    auction_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Payment | None:
    stmt = select(Payment).where(Payment.auction_id == auction_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_stripe_payment_intent_id(
    session: AsyncSession,
    stripe_payment_intent_id: str,
    *,
    for_update: bool = False,
) -> Payment | None:
    stmt = select(Payment).where(
        Payment.stripe_payment_intent_id == stripe_payment_intent_id
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
