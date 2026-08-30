import asyncio
import json
import os
import subprocess
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import aio_pika
import httpx
import psycopg
import pytest

from auction.config.settings import settings
from auction.constants import (
    HEADER_LAST_ERROR,
    HEADER_ORIGINAL_ROUTING_KEY,
    HEADER_RETRY_COUNT,
    QUEUE_DLQ,
    QUEUE_PAYMENT_METHOD,
)
from auction.messaging.envelope import build_envelope
from auction.messaging.topology import declare_topology
from tests.conftest import AUCTION_ROOT, DATABASE_URL
from tests.e2e.test_bidding import _bid, _create_open_auction
from tests.e2e.test_close_worker import _stop_worker

SHORT_RETRY_DELAYS = "0.2,0.2,0.2"


def _sync_dsn() -> str:
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def _start_eligibility_consumer() -> subprocess.Popen[bytes]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(AUCTION_ROOT / "src"),
        "RABBITMQ_URL": settings.rabbitmq_url,
        "RABBITMQ_RETRY_DELAYS": SHORT_RETRY_DELAYS,
    }
    return subprocess.Popen(
        ["uv", "run", "python", "-m", "auction.workers.eligibility_consumer"],
        cwd=AUCTION_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


async def _publish_invalid_payment_method(user_id: str) -> None:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await declare_topology(channel, SHORT_RETRY_DELAYS)
        exchange = await channel.get_exchange("live-auction.events")
        envelope = build_envelope(
            event_id=str(uuid.uuid4()),
            event_type="PaymentMethodReady",
            event_version="v1",
            occurred_at=datetime.now(UTC).isoformat(),
            correlation_id=str(uuid.uuid4()),
            producer="settlement",
            aggregate_id=user_id,
            payload={},
        )
        message = aio_pika.Message(
            body=json.dumps(envelope).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(
            message, routing_key="payment_method.ready.v1", mandatory=True
        )
    finally:
        await connection.close()


async def _wait_dlq_message(timeout: float = 8) -> aio_pika.IncomingMessage:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await declare_topology(channel, SHORT_RETRY_DELAYS)
        dlq = await channel.get_queue(QUEUE_DLQ)
        deadline = time.time() + timeout
        while time.time() < deadline:
            message = await dlq.get(timeout=1, fail=False)
            if message is not None:
                await message.ack()
                return message
        raise AssertionError("poison message did not reach the DLQ")
    finally:
        await connection.close()


async def _purge_retry_queues() -> None:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await declare_topology(channel, SHORT_RETRY_DELAYS)
        payment_method = await channel.get_queue(QUEUE_PAYMENT_METHOD)
        dlq = await channel.get_queue(QUEUE_DLQ)
        await payment_method.purge()
        await dlq.purge()
    finally:
        await connection.close()


async def _payment_method_queue_depth() -> int:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        queue = await channel.declare_queue(
            QUEUE_PAYMENT_METHOD, durable=True, passive=True
        )
        return queue.declaration_result.message_count
    finally:
        await connection.close()


def _bidder_has_projection(user_id: str) -> bool:
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM bidder_payment_status WHERE user_id = %s",
                [user_id],
            )
            return cur.fetchone() is not None


@pytest.fixture
def eligibility_consumer() -> Iterator[subprocess.Popen[bytes]]:
    asyncio.run(_purge_retry_queues())
    process = _start_eligibility_consumer()
    try:
        yield process
    finally:
        _stop_worker(process)


def test_invalid_payment_method_event_reaches_dlq(
    client: httpx.Client, eligibility_consumer: subprocess.Popen[bytes]
) -> None:
    seller_id = str(uuid.uuid4())
    bidder_id = str(uuid.uuid4())
    auction_id = _create_open_auction(client, seller_id)

    asyncio.run(_publish_invalid_payment_method(bidder_id))
    message = asyncio.run(_wait_dlq_message())
    headers = message.headers or {}
    assert int(headers[HEADER_RETRY_COUNT]) == 3
    assert headers[HEADER_ORIGINAL_ROUTING_KEY] == "payment_method.ready.v1"
    assert headers[HEADER_LAST_ERROR]
    assert HEADER_RETRY_COUNT.encode() not in message.body
    assert asyncio.run(_payment_method_queue_depth()) == 0
    assert _bidder_has_projection(bidder_id) is False
    rejected = _bid(client, auction_id, bidder_id, 1100, str(uuid.uuid4()))
    assert rejected.status_code == 403
    assert eligibility_consumer.poll() is None
