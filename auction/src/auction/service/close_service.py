from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from auction.constants import (
    AUCTION_STATUS_PAYMENT_PENDING,
    AUCTION_STATUS_UNSOLD,
    CURRENCY_USD,
    EVENT_TYPE_AUCTION_ENDED,
    EVENT_VERSION_V1,
)
from auction.repository.auction_repository import claim_expired_open
from auction.repository.outbox_repository import insert_outbox


async def close_expired_batch(session: AsyncSession, batch_size: int) -> int:
    auctions = await claim_expired_open(session, batch_size)
    ended_at = datetime.now(UTC)
    for auction in auctions:
        if auction.current_winner_id is None:
            auction.status = AUCTION_STATUS_UNSOLD
            continue
        auction.status = AUCTION_STATUS_PAYMENT_PENDING
        auction.winner_id = auction.current_winner_id
        auction.final_amount_cents = auction.current_price_cents
        await insert_outbox(
            session,
            EVENT_TYPE_AUCTION_ENDED,
            EVENT_VERSION_V1,
            auction.id,
            {
                "auction_id": str(auction.id),
                "winner_id": str(auction.winner_id),
                "final_amount_cents": auction.final_amount_cents,
                "currency": CURRENCY_USD,
                "ended_at": ended_at.isoformat(),
            },
        )
    await session.flush()
    return len(auctions)
