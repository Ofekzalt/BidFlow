import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auction.entity import Bid, IdempotencyKey


async def insert_bid(
    session: AsyncSession,
    auction_id: uuid.UUID,
    bidder_id: uuid.UUID,
    amount_cents: int,
) -> Bid:
    bid = Bid(
        auction_id=auction_id,
        bidder_id=bidder_id,
        amount_cents=amount_cents,
    )
    session.add(bid)
    await session.flush()
    return bid


async def get_idempotency_key(
    session: AsyncSession,
    user_id: uuid.UUID,
    endpoint: str,
    key: str,
) -> IdempotencyKey | None:
    result = await session.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.key == key,
        )
    )
    return result.scalar_one_or_none()


async def insert_idempotency_key(
    session: AsyncSession,
    user_id: uuid.UUID,
    endpoint: str,
    key: str,
    request_hash: str,
    status_code: int,
    response_body: str,
) -> IdempotencyKey:
    record = IdempotencyKey(
        user_id=user_id,
        endpoint=endpoint,
        key=key,
        request_hash=request_hash,
        status_code=status_code,
        response_body=response_body,
    )
    session.add(record)
    await session.flush()
    return record
