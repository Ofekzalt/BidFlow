import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auction.config import get_session
from auction.constants import AUCTION_ROUTER_PREFIX
from auction.dependencies import require_user_id
from auction.dto import (
    AuctionResponse,
    CreateAuctionRequest,
    CurrentBidResponse,
    PatchAuctionRequest,
)
from auction.service import (
    create_auction,
    get_auction,
    list_auctions,
    open_auction,
    patch_auction,
)

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
SellerId = Annotated[str, Depends(require_user_id)]


@router.post(
    AUCTION_ROUTER_PREFIX,
    response_model=AuctionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    body: CreateAuctionRequest,
    session: Session,
    seller_id: SellerId,
) -> AuctionResponse:
    auction = await create_auction(
        session,
        seller_id,
        body.title,
        body.description,
        body.starting_price_cents,
        body.start_time,
        body.end_time,
    )
    return AuctionResponse.model_validate(auction)


@router.get(AUCTION_ROUTER_PREFIX, response_model=list[AuctionResponse])
async def list_auctions_route(session: Session) -> list[AuctionResponse]:
    auctions = await list_auctions(session)
    return [AuctionResponse.model_validate(auction) for auction in auctions]


@router.get(
    f"{AUCTION_ROUTER_PREFIX}/{{auction_id}}/current-bid",
    response_model=CurrentBidResponse,
)
async def get_current_bid(
    auction_id: uuid.UUID, session: Session
) -> CurrentBidResponse:
    auction = await get_auction(session, auction_id)
    return CurrentBidResponse(
        amount_cents=auction.current_price_cents,
        bidder_id=auction.current_winner_id,
    )


@router.patch(
    f"{AUCTION_ROUTER_PREFIX}/{{auction_id}}",
    response_model=AuctionResponse,
)
async def patch(
    auction_id: uuid.UUID,
    body: PatchAuctionRequest,
    session: Session,
    seller_id: SellerId,
) -> AuctionResponse:
    auction = await patch_auction(
        session,
        auction_id,
        seller_id,
        body.title,
        body.description,
        body.starting_price_cents,
        body.start_time,
        body.end_time,
    )
    return AuctionResponse.model_validate(auction)


@router.post(
    f"{AUCTION_ROUTER_PREFIX}/{{auction_id}}/open",
    response_model=AuctionResponse,
)
async def open_auction_route(
    auction_id: uuid.UUID,
    session: Session,
    seller_id: SellerId,
) -> AuctionResponse:
    auction = await open_auction(session, auction_id, seller_id)
    return AuctionResponse.model_validate(auction)


@router.get(
    f"{AUCTION_ROUTER_PREFIX}/{{auction_id}}",
    response_model=AuctionResponse,
)
async def get_auction_route(auction_id: uuid.UUID, session: Session) -> AuctionResponse:
    auction = await get_auction(session, auction_id)
    return AuctionResponse.model_validate(auction)
