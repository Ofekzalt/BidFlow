import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auction.constants import (
    AUCTION_STATUS_DRAFT,
    AUCTION_STATUS_OPEN,
    AUCTION_STATUS_PAYMENT_PENDING,
)
from auction.entity import Auction


async def create(
    session: AsyncSession,
    seller_id: uuid.UUID,
    title: str,
    description: str,
    starting_price_cents: int,
    start_time: datetime,
    end_time: datetime,
) -> Auction:
    auction = Auction(
        seller_id=seller_id,
        title=title,
        description=description,
        starting_price_cents=starting_price_cents,
        current_price_cents=starting_price_cents,
        status=AUCTION_STATUS_DRAFT,
        start_time=start_time,
        end_time=end_time,
    )
    session.add(auction)
    await session.flush()
    return auction


async def get_by_id(
    session: AsyncSession,
    auction_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Auction | None:
    stmt = select(Auction).where(Auction.id == auction_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(session: AsyncSession) -> list[Auction]:
    result = await session.execute(select(Auction).order_by(Auction.created_at.desc()))
    return list[Auction](result.scalars().all())


async def claim_expired_open(session: AsyncSession, limit: int) -> list[Auction]:
    stmt = (
        select(Auction)
        .where(
            Auction.status == AUCTION_STATUS_OPEN,
            Auction.end_time <= func.now(),
        )
        .order_by(Auction.end_time)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    return list[Auction](result.scalars().all())


async def apply_payment_result_if_pending(
    session: AsyncSession, auction_id: uuid.UUID, status: str
) -> None:
    stmt = (
        update(Auction)
        .where(
            Auction.id == auction_id,
            Auction.status == AUCTION_STATUS_PAYMENT_PENDING,
        )
        .values(status=status)
    )
    await session.execute(stmt)
