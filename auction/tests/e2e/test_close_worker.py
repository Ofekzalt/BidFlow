import asyncio
import os
import signal
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import psycopg
import pytest

from auction.config.settings import settings
from auction.constants import USER_ID_HEADER
from auction.service import apply_payment_status
from tests.conftest import DATABASE_URL

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
AUCTION_SERVICE_ROOT = Path(__file__).resolve().parents[2]


def _sync_dsn() -> str:
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


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


def _mark_ready(user_id: str) -> None:
    async def scenario() -> None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy.pool import NullPool

        engine = create_async_engine(
            settings.database_url, pool_pre_ping=True, poolclass=NullPool
        )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as session:
                await apply_payment_status(
                    session, uuid.uuid4(), uuid.UUID(user_id), True, 1
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


def _expire(auction_id: str) -> None:
    past = datetime.now(UTC) - timedelta(minutes=1)
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE auctions SET end_time = %s WHERE id = %s",
                [past, auction_id],
            )
        conn.commit()


def _auction_status(auction_id: str) -> dict:
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, winner_id, final_amount_cents "
                "FROM auctions WHERE id = %s",
                [auction_id],
            )
            row = cur.fetchone()
            assert row is not None
            return {"status": row[0], "winner_id": row[1], "final_amount_cents": row[2]}


def _assert_close_invariants(auction_ids: list[str]) -> None:
    for auction_id in auction_ids:
        state = _auction_status(auction_id)
        if state["status"] == "OPEN":
            continue
        if state["status"] == "UNSOLD":
            assert state["winner_id"] is None
            assert state["final_amount_cents"] is None
            assert _outbox_rows(auction_id) == []
            continue
        if state["status"] == "PAYMENT_PENDING":
            assert state["winner_id"] is not None
            assert state["final_amount_cents"] is not None
            assert len(_outbox_rows(auction_id)) == 1
            continue
        raise AssertionError(f"unexpected status for {auction_id}: {state['status']}")


def _outbox_rows(auction_id: str | None = None) -> list[tuple]:
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            if auction_id is None:
                cur.execute(
                    "SELECT aggregate_id, event_type, event_version, "
                    "published_at, payload FROM outbox_events"
                )
            else:
                cur.execute(
                    "SELECT aggregate_id, event_type, event_version, "
                    "published_at, payload FROM outbox_events "
                    "WHERE aggregate_id = %s",
                    [auction_id],
                )
            return list(cur.fetchall())


def _start_worker(*, batch_size: int = 50) -> subprocess.Popen[bytes]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(AUCTION_SERVICE_ROOT / "src"),
        "CLOSE_POLL_INTERVAL_SECONDS": "0.2",
        "CLOSE_BATCH_SIZE": str(batch_size),
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "auction.workers.close_worker"],
        cwd=AUCTION_SERVICE_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return process


def _stop_worker(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _wait_status(
    client: httpx.Client, auction_id: str, expected: str, timeout: float = 8
) -> dict:
    deadline = time.time() + timeout
    last: dict | None = None
    while time.time() < deadline:
        response = client.get(f"/auctions/{auction_id}")
        assert response.status_code == 200
        last = response.json()
        if last["status"] == expected:
            return last
        time.sleep(0.1)
    raise AssertionError(f"auction {auction_id} status {last} != {expected}")


@pytest.fixture
def close_worker() -> Iterator[subprocess.Popen[bytes]]:
    process = _start_worker()
    try:
        yield process
    finally:
        _stop_worker(process)


def test_close_worker_closes_expired_auctions(
    client: httpx.Client, close_worker: subprocess.Popen[bytes]
) -> None:
    seller_id = str(uuid.uuid4())
    bidder_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    unsold_id = _create_open_auction(
        client,
        seller_id,
        title="Expired unsold",
        start_time=(now - timedelta(days=2)).isoformat(),
        end_time=(now - timedelta(hours=1)).isoformat(),
    )
    live_id = _create_open_auction(client, seller_id, title="Still open")
    draft = client.post(
        "/auctions",
        headers={USER_ID_HEADER: seller_id},
        json=_auction_body(
            title="Expired draft",
            start_time=(now - timedelta(days=2)).isoformat(),
            end_time=(now - timedelta(hours=1)).isoformat(),
        ),
    )
    assert draft.status_code == 201
    draft_id = draft.json()["id"]

    _mark_ready(bidder_id)
    winner_id = _create_open_auction(client, seller_id, title="Has winner")
    bid = client.post(
        f"/auctions/{winner_id}/bids",
        headers={
            USER_ID_HEADER: bidder_id,
            IDEMPOTENCY_KEY_HEADER: str(uuid.uuid4()),
        },
        json={"amount_cents": 1100},
    )
    assert bid.status_code == 201
    _expire(winner_id)

    unsold = _wait_status(client, unsold_id, "UNSOLD")
    assert unsold["winner_id"] is None
    assert unsold["final_amount_cents"] is None
    assert _outbox_rows(unsold_id) == []

    pending = _wait_status(client, winner_id, "PAYMENT_PENDING")
    assert pending["winner_id"] == bidder_id
    assert pending["final_amount_cents"] == 1100
    assert pending["current_winner_id"] == bidder_id
    assert pending["current_price_cents"] == 1100
    rows = _outbox_rows(winner_id)
    assert len(rows) == 1
    _, event_type, event_version, published_at, payload = rows[0]
    assert event_type == "AuctionEnded"
    assert event_version == "v1"
    assert published_at is None
    assert payload["auction_id"] == winner_id
    assert payload["winner_id"] == bidder_id
    assert payload["final_amount_cents"] == 1100
    assert payload["currency"] == "USD"
    assert payload["ended_at"]

    assert client.get(f"/auctions/{live_id}").json()["status"] == "OPEN"
    assert client.get(f"/auctions/{draft_id}").json()["status"] == "DRAFT"
    assert (
        client.post(
            f"/auctions/{unsold_id}/bids",
            headers={
                USER_ID_HEADER: bidder_id,
                IDEMPOTENCY_KEY_HEADER: str(uuid.uuid4()),
            },
            json={"amount_cents": 1200},
        ).status_code
        == 409
    )

    time.sleep(0.6)
    assert len(_outbox_rows(winner_id)) == 1
    assert client.get(f"/auctions/{winner_id}").json()["final_amount_cents"] == 1100
    assert close_worker.poll() is None


def test_two_close_workers_claim_each_auction_once(client: httpx.Client) -> None:
    seller_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    unsold_ids = [
        _create_open_auction(
            client,
            seller_id,
            title=f"Unsold {i}",
            start_time=(now - timedelta(days=2)).isoformat(),
            end_time=(now - timedelta(hours=1)).isoformat(),
        )
        for i in range(6)
    ]
    winner_ids: list[str] = []
    for i in range(4):
        bidder_id = str(uuid.uuid4())
        _mark_ready(bidder_id)
        auction_id = _create_open_auction(client, seller_id, title=f"Won {i}")
        bid = client.post(
            f"/auctions/{auction_id}/bids",
            headers={
                USER_ID_HEADER: bidder_id,
                IDEMPOTENCY_KEY_HEADER: str(uuid.uuid4()),
            },
            json={"amount_cents": 1100 + i},
        )
        assert bid.status_code == 201
        _expire(auction_id)
        winner_ids.append(auction_id)

    workers = [_start_worker(batch_size=1), _start_worker(batch_size=1)]
    try:
        for auction_id in unsold_ids:
            _wait_status(client, auction_id, "UNSOLD")
        for auction_id in winner_ids:
            _wait_status(client, auction_id, "PAYMENT_PENDING")
    finally:
        for worker in workers:
            _stop_worker(worker)

    all_ids = unsold_ids + winner_ids
    statuses = [
        client.get(f"/auctions/{auction_id}").json()["status"] for auction_id in all_ids
    ]
    assert statuses == ["UNSOLD"] * 6 + ["PAYMENT_PENDING"] * 4
    rows = _outbox_rows()
    assert {str(row[0]) for row in rows} == set(winner_ids)
    assert len(rows) == 4


def test_close_worker_exits_on_sigterm() -> None:
    process = _start_worker()
    time.sleep(1.0)
    assert process.poll() is None
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=5) == 0


def test_close_worker_sigterm_during_batch_leaves_atomic_state(
    client: httpx.Client,
) -> None:
    seller_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    auction_ids = [
        _create_open_auction(
            client,
            seller_id,
            title=f"Batch {i}",
            start_time=(now - timedelta(days=2)).isoformat(),
            end_time=(now - timedelta(hours=1)).isoformat(),
        )
        for i in range(12)
    ]
    process = _start_worker(batch_size=1)
    try:
        deadline = time.time() + 6
        while time.time() < deadline:
            closed = sum(
                1
                for auction_id in auction_ids
                if _auction_status(auction_id)["status"] != "OPEN"
            )
            if 2 <= closed < len(auction_ids):
                process.send_signal(signal.SIGTERM)
                assert process.wait(timeout=5) == 0
                break
            time.sleep(0.1)
        else:
            raise AssertionError("worker did not close enough auctions before timeout")
    finally:
        if process.poll() is None:
            _stop_worker(process)

    _assert_close_invariants(auction_ids)
