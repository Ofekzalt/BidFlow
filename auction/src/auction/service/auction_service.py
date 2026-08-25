import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from auction.constants import (
    AUCTION_STATUS_DRAFT,
    AUCTION_STATUS_OPEN,
    ERROR_START_BEFORE_END,
)
from auction.entity import Auction
from auction.exception import (
    AuctionNotDraftError,
    AuctionNotFoundError,
    AuctionValidationError,
    ForbiddenError,
)
from auction.repository import create, get_by_id, list_all


async def create_auction(
    session: AsyncSession,
    seller_id: str,
    title: str,
    description: str,
    starting_price_cents: int,
    start_time: datetime,
    end_time: datetime,
) -> Auction:
    return await create(
        session,
        uuid.UUID(seller_id),
        title,
        description,
        starting_price_cents,
        start_time,
        end_time,
    )


async def get_auction(session: AsyncSession, auction_id: uuid.UUID) -> Auction:
    auction = await get_by_id(session, auction_id)
    if auction is None:
        raise AuctionNotFoundError()
    return auction


async def list_auctions(session: AsyncSession) -> list[Auction]:
    return await list_all(session)


def _require_seller(auction: Auction, seller_id: str) -> None:
    if auction.seller_id != uuid.UUID(seller_id):
        raise ForbiddenError()


def _require_draft(auction: Auction) -> None:
    if auction.status != AUCTION_STATUS_DRAFT:
        raise AuctionNotDraftError()


async def patch_auction(
    session: AsyncSession,
    auction_id: uuid.UUID,
    seller_id: str,
    title: str | None,
    description: str | None,
    starting_price_cents: int | None,
    start_time: datetime | None,
    end_time: datetime | None,
) -> Auction:
    auction = await get_auction(session, auction_id)
    _require_seller(auction, seller_id)
    _require_draft(auction)
    if title is not None:
        auction.title = title
    if description is not None:
        auction.description = description
    if starting_price_cents is not None:
        auction.starting_price_cents = starting_price_cents
        auction.current_price_cents = starting_price_cents
    if start_time is not None:
        auction.start_time = start_time
    if end_time is not None:
        auction.end_time = end_time
    if auction.start_time >= auction.end_time:
        raise AuctionValidationError(ERROR_START_BEFORE_END)
    await session.flush()
    await session.refresh(auction)
    return auction


async def open_auction(
    session: AsyncSession,
    auction_id: uuid.UUID,
    seller_id: str,
) -> Auction:
    auction = await get_auction(session, auction_id)
    _require_seller(auction, seller_id)
    _require_draft(auction)
    auction.status = AUCTION_STATUS_OPEN
    await session.flush()
    await session.refresh(auction)
    return auction
