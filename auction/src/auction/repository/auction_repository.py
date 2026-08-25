import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auction.constants import AUCTION_STATUS_DRAFT
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


async def get_by_id(session: AsyncSession, auction_id: uuid.UUID) -> Auction | None:
    result = await session.execute(select(Auction).where(Auction.id == auction_id))
    return result.scalar_one_or_none()


async def list_all(session: AsyncSession) -> list[Auction]:
    result = await session.execute(select(Auction).order_by(Auction.created_at.desc()))
    return list[Auction](result.scalars().all())
