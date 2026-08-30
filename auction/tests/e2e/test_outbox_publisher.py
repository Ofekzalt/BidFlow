import asyncio
import json
import os
import subprocess
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import aio_pika
import httpx
import pytest

from auction.config.settings import settings
from auction.constants import USER_ID_HEADER
from tests.conftest import AUCTION_ROOT, DATABASE_URL
from tests.e2e.test_close_worker import (
    _create_open_auction,
    _expire,
    _mark_ready,
    _outbox_rows,
    _stop_worker,
    _wait_status,
)
from tests.e2e.test_close_worker import (
    _start_worker as _start_close_worker,
)

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
RETRY_HEADER_NAMES = ("x-retry-count", "x-original-routing-key", "x-last-error")
REPO_ROOT = (
    AUCTION_ROOT
    if (AUCTION_ROOT / "docker-compose.yml").exists()
    else AUCTION_ROOT.parent
)


def _sync_dsn() -> str:
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def _start_outbox_worker() -> subprocess.Popen[bytes]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(AUCTION_ROOT / "src"),
        "OUTBOX_POLL_INTERVAL_SECONDS": "0.2",
        "OUTBOX_BATCH_SIZE": "50",
        "RABBITMQ_URL": settings.rabbitmq_url,
    }
    return subprocess.Popen(
        ["uv", "run", "python", "-m", "auction.workers.outbox_worker"],
        cwd=AUCTION_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _published_at(auction_id: str) -> datetime | None:
    rows = _outbox_rows(auction_id)
    assert len(rows) == 1
    return rows[0][3]


def _wait_published(auction_id: str, timeout: float = 8) -> datetime:
    deadline = time.time() + timeout
    while time.time() < deadline:
        published_at = _published_at(auction_id)
        if published_at is not None:
            return published_at
        time.sleep(0.1)
    raise AssertionError("outbox row was not marked published")


async def _purge_auction_ended_queue() -> None:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        queue = await channel.declare_queue("settlement.auction-ended", durable=True)
        await queue.purge()
    finally:
        await connection.close()


async def _get_auction_ended_message(timeout: float = 8) -> aio_pika.IncomingMessage:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        queue = await channel.declare_queue("settlement.auction-ended", durable=True)
        message = await queue.get(timeout=timeout, fail=False)
        if message is not None:
            await message.ack()
        return message
    finally:
        await connection.close()


def _compose(*args: str) -> None:
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"docker compose {' '.join(args)} failed: "
            f"{result.stderr or result.stdout}"
        )


async def _ping_rabbitmq() -> None:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    await connection.close()


def _wait_rabbitmq(timeout: float = 30) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            asyncio.run(_ping_rabbitmq())
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise AssertionError(f"rabbitmq did not become ready: {last_error}")


@pytest.fixture
def close_worker() -> Iterator[subprocess.Popen[bytes]]:
    process = _start_close_worker()
    try:
        yield process
    finally:
        _stop_worker(process)


def test_outbox_worker_publishes_auction_ended(
    client: httpx.Client, close_worker: subprocess.Popen[bytes]
) -> None:
    seller_id = str(uuid.uuid4())
    bidder_id = str(uuid.uuid4())
    _mark_ready(bidder_id)
    auction_id = _create_open_auction(client, seller_id, title="Publish winner")
    bid = client.post(
        f"/auctions/{auction_id}/bids",
        headers={
            USER_ID_HEADER: bidder_id,
            IDEMPOTENCY_KEY_HEADER: str(uuid.uuid4()),
        },
        json={"amount_cents": 1100},
    )
    assert bid.status_code == 201
    _expire(auction_id)
    _wait_status(client, auction_id, "PAYMENT_PENDING")
    assert _published_at(auction_id) is None
    asyncio.run(_purge_auction_ended_queue())

    unsold_id = _create_open_auction(
        client,
        seller_id,
        title="Unsold no event",
        start_time=(datetime.now(UTC) - timedelta(days=2)).isoformat(),
        end_time=(datetime.now(UTC) - timedelta(hours=1)).isoformat(),
    )
    _wait_status(client, unsold_id, "UNSOLD")
    assert _outbox_rows(unsold_id) == []

    worker = _start_outbox_worker()
    try:
        published_at = _wait_published(auction_id)
        message = asyncio.run(_get_auction_ended_message())
        assert message is not None
        envelope = json.loads(message.body)
        payload = envelope["payload"]
        assert envelope["event_type"] == "AuctionEnded"
        assert envelope["event_version"] == "v1"
        assert envelope["producer"] == "auction"
        assert envelope["aggregate_id"] == auction_id
        assert envelope["event_id"]
        assert envelope["occurred_at"]
        assert envelope["correlation_id"]
        assert payload["auction_id"] == auction_id
        assert payload["winner_id"] == bidder_id
        assert payload["final_amount_cents"] == 1100
        assert payload["currency"] == "USD"
        assert payload["ended_at"]
        for name in RETRY_HEADER_NAMES:
            assert name not in envelope
            assert name not in payload
        assert published_at.tzinfo is not None
    finally:
        _stop_worker(worker)


def test_outbox_worker_keeps_row_unpublished_when_broker_is_down(
    client: httpx.Client, close_worker: subprocess.Popen[bytes]
) -> None:
    seller_id = str(uuid.uuid4())
    bidder_id = str(uuid.uuid4())
    _mark_ready(bidder_id)
    auction_id = _create_open_auction(client, seller_id, title="Broker down")
    bid = client.post(
        f"/auctions/{auction_id}/bids",
        headers={
            USER_ID_HEADER: bidder_id,
            IDEMPOTENCY_KEY_HEADER: str(uuid.uuid4()),
        },
        json={"amount_cents": 1100},
    )
    assert bid.status_code == 201
    _expire(auction_id)
    _wait_status(client, auction_id, "PAYMENT_PENDING")
    assert _published_at(auction_id) is None
    asyncio.run(_purge_auction_ended_queue())

    _compose("stop", "rabbitmq")
    try:
        worker = _start_outbox_worker()
        try:
            time.sleep(1.2)
            assert _published_at(auction_id) is None
        finally:
            _stop_worker(worker)
    finally:
        _compose("start", "rabbitmq")
        _wait_rabbitmq()

    worker = _start_outbox_worker()
    try:
        _wait_published(auction_id)
        message = asyncio.run(_get_auction_ended_message())
        assert message is not None
        envelope = json.loads(message.body)
        assert envelope["payload"]["auction_id"] == auction_id
    finally:
        _stop_worker(worker)
