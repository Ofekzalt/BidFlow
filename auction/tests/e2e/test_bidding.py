import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta

import httpx
import psycopg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from auction.config.settings import settings
from auction.constants import MAX_CENTS, USER_ID_HEADER
from auction.service import apply_payment_status

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
SessionFactory = async_sessionmaker[AsyncSession]


def _auction_body(**overrides: object) -> dict:
    now = datetime.now(UTC)
    body: dict = {
        "title": "Vintage watch",
        "description": "A timed English auction listing",
        "starting_price_cents": 1000,
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(days=1)).isoformat(),
    }
    body.update(overrides)
    return body


def _session_factory() -> tuple[SessionFactory, object]:
    engine = create_async_engine(
        settings.database_url, pool_pre_ping=True, poolclass=NullPool
    )
    return async_sessionmaker(engine, expire_on_commit=False), engine


def _mark_ready(user_id: str, ready: bool = True, version: int = 1) -> None:
    async def scenario() -> None:
        sessions, engine = _session_factory()
        try:
            async with sessions() as session:
                await apply_payment_status(
                    session,
                    uuid.uuid4(),
                    uuid.UUID(user_id),
                    ready,
                    version,
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def _create_open_auction(
    client: httpx.Client, seller_id: str, **body_overrides: object
) -> str:
    created = client.post(
        "/auctions",
        headers={USER_ID_HEADER: seller_id},
        json=_auction_body(**body_overrides),
    )
    assert created.status_code == 201
    auction_id = created.json()["id"]
    opened = client.post(
        f"/auctions/{auction_id}/open",
        headers={USER_ID_HEADER: seller_id},
    )
    assert opened.status_code == 200
    return auction_id


def _bid(
    client: httpx.Client,
    auction_id: str,
    bidder_id: str,
    amount_cents: int,
    idempotency_key: str | None = None,
) -> httpx.Response:
    headers = {USER_ID_HEADER: bidder_id}
    if idempotency_key is not None:
        headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key
    return client.post(
        f"/auctions/{auction_id}/bids",
        headers=headers,
        json={"amount_cents": amount_cents},
    )


def _bid_count(auction_id: str, bidder_id: str | None = None) -> int:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            if bidder_id is None:
                cur.execute(
                    "SELECT COUNT(*) FROM bids WHERE auction_id = %s",
                    [auction_id],
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM bids "
                    "WHERE auction_id = %s AND bidder_id = %s",
                    [auction_id, bidder_id],
                )
            return cur.fetchone()[0]


def test_bidding(client: httpx.Client) -> None:
    seller_id = str(uuid.uuid4())
    bidder_id = str(uuid.uuid4())
    other_id = str(uuid.uuid4())
    auction_id = _create_open_auction(client, seller_id)
    _mark_ready(bidder_id)

    draft_created = client.post(
        "/auctions",
        headers={USER_ID_HEADER: seller_id},
        json=_auction_body(title="Draft only"),
    )
    assert draft_created.status_code == 201
    draft_id = draft_created.json()["id"]
    assert (
        _bid(
            client, draft_id, bidder_id, 1100, idempotency_key=str(uuid.uuid4())
        ).status_code
        == 409
    )

    assert _bid(client, auction_id, bidder_id, 1100).status_code == 422
    assert (
        _bid(
            client, auction_id, bidder_id, 0, idempotency_key=str(uuid.uuid4())
        ).status_code
        == 422
    )
    assert (
        _bid(
            client,
            auction_id,
            bidder_id,
            MAX_CENTS + 1,
            idempotency_key=str(uuid.uuid4()),
        ).status_code
        == 422
    )

    assert (
        _bid(
            client, auction_id, other_id, 1100, idempotency_key=str(uuid.uuid4())
        ).status_code
        == 403
    )
    assert (
        _bid(
            client, auction_id, seller_id, 1100, idempotency_key=str(uuid.uuid4())
        ).status_code
        == 403
    )

    now = datetime.now(UTC)
    late_id = _create_open_auction(
        client,
        seller_id,
        title="Already ended",
        start_time=(now - timedelta(days=2)).isoformat(),
        end_time=(now - timedelta(hours=1)).isoformat(),
    )
    assert (
        _bid(
            client, late_id, bidder_id, 1100, idempotency_key=str(uuid.uuid4())
        ).status_code
        == 409
    )

    assert (
        _bid(
            client, auction_id, bidder_id, 1000, idempotency_key=str(uuid.uuid4())
        ).status_code
        == 422
    )

    accepted = _bid(
        client, auction_id, bidder_id, 1100, idempotency_key=str(uuid.uuid4())
    )
    assert accepted.status_code == 201
    payload = accepted.json()
    assert payload["amount_cents"] == 1100
    assert payload["bidder_id"] == bidder_id
    assert payload["auction_id"] == auction_id

    current = client.get(f"/auctions/{auction_id}/current-bid")
    assert current.status_code == 200
    assert current.json()["amount_cents"] == 1100
    assert current.json()["bidder_id"] == bidder_id

    key = str(uuid.uuid4())
    first = _bid(client, auction_id, bidder_id, 1200, idempotency_key=key)
    second = _bid(client, auction_id, bidder_id, 1200, idempotency_key=key)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()
    mismatch = _bid(client, auction_id, bidder_id, 1300, idempotency_key=key)
    assert mismatch.status_code == 409
    assert _bid_count(auction_id) == 2

    amounts = [1400, 1800, 1500]
    bidders = [str(uuid.uuid4()) for _ in amounts]
    for ready_bidder in bidders:
        _mark_ready(ready_bidder)

    def place(bidder: str, amount: int) -> httpx.Response:
        with httpx.Client(base_url=str(client.base_url), timeout=10.0) as http_client:
            return _bid(
                http_client,
                auction_id,
                bidder,
                amount,
                idempotency_key=str(uuid.uuid4()),
            )

    with ThreadPoolExecutor(max_workers=len(bidders)) as pool:
        results = [
            future.result()
            for future in as_completed(
                pool.submit(place, bidder, amount)
                for bidder, amount in zip(bidders, amounts, strict=True)
            )
        ]

    assert all(result.status_code in {201, 422} for result in results)
    assert any(result.status_code == 201 for result in results)
    current = client.get(f"/auctions/{auction_id}/current-bid")
    assert current.status_code == 200
    assert current.json()["amount_cents"] == 1800
    assert current.json()["bidder_id"] == bidders[amounts.index(1800)]

    storm_bidder = str(uuid.uuid4())
    _mark_ready(storm_bidder)
    storm_key = str(uuid.uuid4())

    def duplicate() -> httpx.Response:
        with httpx.Client(base_url=str(client.base_url), timeout=10.0) as http_client:
            return _bid(
                http_client,
                auction_id,
                storm_bidder,
                1900,
                idempotency_key=storm_key,
            )

    with ThreadPoolExecutor(max_workers=16) as pool:
        storm_results = [
            future.result()
            for future in as_completed(pool.submit(duplicate) for _ in range(50))
        ]

    assert all(result.status_code == 201 for result in storm_results)
    bodies = [result.json() for result in storm_results]
    assert all(body == bodies[0] for body in bodies)
    assert _bid_count(auction_id, storm_bidder) == 1
