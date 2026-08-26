import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from auction.constants import AUCTION_STATUS_OPEN
from auction.dto import BidResponse
from auction.entity import IdempotencyKey
from auction.exception import (
    AuctionEndedError,
    AuctionNotOpenError,
    BidTooLowError,
    ForbiddenError,
    IdempotencyConflictError,
    PaymentNotReadyError,
)
from auction.repository import (
    get_idempotency_key,
    insert_bid,
    insert_idempotency_key,
)
from auction.service.auction_service import get_auction
from auction.service.payment_status_service import is_payment_ready


def _bid_endpoint(auction_id: uuid.UUID) -> str:
    return f"POST /auctions/{auction_id}/bids"


def _request_hash(amount_cents: int) -> str:
    payload = json.dumps({"amount_cents": amount_cents}, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _replay_or_conflict(
    existing: IdempotencyKey,
    request_hash: str,
) -> BidResponse:
    if existing.request_hash != request_hash:
        raise IdempotencyConflictError()
    return BidResponse.model_validate_json(existing.response_body)


async def place_bid(
    session: AsyncSession,
    auction_id: uuid.UUID,
    bidder_id: uuid.UUID,
    amount_cents: int,
    idempotency_key: str,
) -> BidResponse:
    endpoint = _bid_endpoint(auction_id)
    request_hash = _request_hash(amount_cents)

    existing = await get_idempotency_key(session, bidder_id, endpoint, idempotency_key)
    if existing is not None:
        return _replay_or_conflict(existing, request_hash)

    auction = await get_auction(session, auction_id, for_update=True)

    existing = await get_idempotency_key(session, bidder_id, endpoint, idempotency_key)
    if existing is not None:
        return _replay_or_conflict(existing, request_hash)

    if auction.status != AUCTION_STATUS_OPEN:
        raise AuctionNotOpenError()
    if datetime.now(UTC) >= auction.end_time:
        raise AuctionEndedError()
    if auction.seller_id == bidder_id:
        raise ForbiddenError()
    if amount_cents <= auction.current_price_cents:
        raise BidTooLowError()
    if not await is_payment_ready(session, bidder_id):
        raise PaymentNotReadyError()

    bid = await insert_bid(session, auction.id, bidder_id, amount_cents)
    auction.current_price_cents = bid.amount_cents
    auction.current_winner_id = bid.bidder_id
    await session.flush()

    response = BidResponse(
        auction_id=auction.id,
        bidder_id=bid.bidder_id,
        amount_cents=bid.amount_cents,
    )
    await insert_idempotency_key(
        session,
        bidder_id,
        endpoint,
        idempotency_key,
        request_hash,
        201,
        response.model_dump_json(),
    )
    return response
