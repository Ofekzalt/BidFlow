import asyncio
import json
import os
import subprocess
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import aio_pika
import psycopg
import pytest
from psycopg.types.json import Jsonb

from settlement.messaging.topology import declare_topology
from tests.conftest import DATABASE_URL, SETTLEMENT_ROOT

os.environ.setdefault("DATABASE_URL", DATABASE_URL)

RETRY_HEADER_NAMES = ("x-retry-count", "x-original-routing-key", "x-last-error")
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
QUEUE_AUCTION_ENDED = "settlement.auction-ended"
QUEUE_PAYMENT_METHOD = "auction.payment-method"


def _sync_dsn(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


def _start_worker(module: str) -> subprocess.Popen[bytes]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(SETTLEMENT_ROOT / "src"),
        "RABBITMQ_URL": RABBITMQ_URL,
        "OUTBOX_POLL_INTERVAL_SECONDS": "0.2",
        "OUTBOX_BATCH_SIZE": "50",
        "RABBITMQ_RETRY_DELAYS": "0.2,0.2,0.2",
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
    }
    return subprocess.Popen(
        ["uv", "run", "python", "-m", module],
        cwd=SETTLEMENT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _stop_worker(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _insert_outbox(
    event_id: uuid.UUID,
    event_type: str,
    aggregate_id: uuid.UUID,
    payload: dict[str, object],
) -> None:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outbox_events (
                    id, event_type, event_version, aggregate_id, payload
                )
                VALUES (%s, %s, 'v1', %s, %s)
                """,
                [event_id, event_type, aggregate_id, Jsonb(payload)],
            )
        conn.commit()


def _published_at(event_id: uuid.UUID) -> datetime | None:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT published_at FROM outbox_events WHERE id = %s",
                [event_id],
            )
            row = cur.fetchone()
    if row is None:
        return None
    return row[0]


def _wait_published(event_id: uuid.UUID, timeout: float = 8) -> datetime:
    deadline = time.time() + timeout
    while time.time() < deadline:
        published_at = _published_at(event_id)
        if published_at is not None:
            return published_at
        time.sleep(0.1)
    raise AssertionError("outbox row was not marked published")


def _processed_event_count(event_id: uuid.UUID) -> int:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM processed_events WHERE event_id = %s",
                [event_id],
            )
            row = cur.fetchone()
    return int(row[0]) if row is not None else 0


def _wait_processed(event_id: uuid.UUID, timeout: float = 8) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _processed_event_count(event_id) == 1:
            return
        time.sleep(0.1)
    raise AssertionError("processed_events was not written")


async def _purge_queue(name: str) -> None:
    connection = await aio_pika.connect(RABBITMQ_URL)
    try:
        channel = await connection.channel()
        await declare_topology(channel, "0.2,0.2,0.2")
        queue = await channel.get_queue(name)
        await queue.purge()
    finally:
        await connection.close()


async def _get_message(queue_name: str, timeout: float = 8) -> aio_pika.IncomingMessage:
    connection = await aio_pika.connect(RABBITMQ_URL)
    try:
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name, durable=True)
        message = await queue.get(timeout=timeout, fail=False)
        if message is not None:
            await message.ack()
        return message
    finally:
        await connection.close()


async def _publish_auction_ended(event_id: uuid.UUID, auction_id: str) -> None:
    connection = await aio_pika.connect(RABBITMQ_URL)
    try:
        channel = await connection.channel()
        await declare_topology(channel, "0.2,0.2,0.2")
        exchange = await channel.get_exchange("live-auction.events")
        envelope = {
            "event_id": str(event_id),
            "event_type": "AuctionEnded",
            "event_version": "v1",
            "occurred_at": datetime.now(UTC).isoformat(),
            "correlation_id": str(uuid.uuid4()),
            "producer": "auction",
            "aggregate_id": auction_id,
            "payload": {
                "auction_id": auction_id,
                "winner_id": str(uuid.uuid4()),
                "final_amount_cents": 1100,
                "currency": "USD",
                "ended_at": datetime.now(UTC).isoformat(),
            },
        }
        message = aio_pika.Message(
            body=json.dumps(envelope).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=str(event_id),
        )
        await exchange.publish(message, routing_key="auction.ended.v1", mandatory=True)
    finally:
        await connection.close()


@pytest.fixture(autouse=True)
def settlement_tables(settlement_schema: None) -> Iterator[None]:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE outbox_events, processed_events")
        conn.commit()
    yield


def test_settlement_outbox_worker_publishes_seeded_row(
    settlement_schema: None,
) -> None:
    event_id = uuid.uuid4()
    user_id = uuid.uuid4()
    _insert_outbox(
        event_id,
        "PaymentMethodReady",
        user_id,
        {"user_id": str(user_id), "version": 1},
    )
    asyncio.run(_purge_queue(QUEUE_PAYMENT_METHOD))
    worker = _start_worker("settlement.workers.outbox_worker")
    try:
        published_at = _wait_published(event_id)
        message = asyncio.run(_get_message(QUEUE_PAYMENT_METHOD))
        assert message is not None
        envelope = json.loads(message.body)
        payload = envelope["payload"]
        assert envelope["event_type"] == "PaymentMethodReady"
        assert envelope["event_version"] == "v1"
        assert envelope["producer"] == "settlement"
        assert envelope["aggregate_id"] == str(user_id)
        assert envelope["event_id"] == str(event_id)
        assert payload["user_id"] == str(user_id)
        assert payload["version"] == 1
        for name in RETRY_HEADER_NAMES:
            assert name not in envelope
            assert name not in payload
        assert published_at.tzinfo is not None
    finally:
        _stop_worker(worker)


def test_auction_ended_consumer_records_duplicates_once(
    settlement_schema: None,
) -> None:
    event_id = uuid.uuid4()
    auction_id = str(uuid.uuid4())
    asyncio.run(_purge_queue(QUEUE_AUCTION_ENDED))
    consumer = _start_worker("settlement.workers.auction_ended_consumer")
    try:
        asyncio.run(_publish_auction_ended(event_id, auction_id))
        _wait_processed(event_id)
        asyncio.run(_publish_auction_ended(event_id, auction_id))
        time.sleep(1.0)
        assert _processed_event_count(event_id) == 1
    finally:
        _stop_worker(consumer)
