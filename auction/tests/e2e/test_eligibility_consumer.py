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
import pytest

from auction.config.settings import settings
from auction.messaging.envelope import build_envelope
from auction.messaging.topology import declare_topology
from tests.conftest import AUCTION_ROOT, DATABASE_URL
from tests.e2e.test_bidding import _bid, _create_open_auction
from tests.e2e.test_close_worker import _stop_worker

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


def _start_eligibility_consumer() -> subprocess.Popen[bytes]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(AUCTION_ROOT / "src"),
        "RABBITMQ_URL": settings.rabbitmq_url,
    }
    return subprocess.Popen(
        ["uv", "run", "python", "-m", "auction.workers.eligibility_consumer"],
        cwd=AUCTION_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


async def _publish_payment_method(
    *,
    event_id: uuid.UUID,
    user_id: str,
    event_type: str,
    version: int,
    routing_key: str,
) -> None:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await declare_topology(channel, settings.rabbitmq_retry_delays)
        exchange = await channel.get_exchange("live-auction.events")
        envelope = build_envelope(
            event_id=str(event_id),
            event_type=event_type,
            event_version="v1",
            occurred_at=datetime.now(UTC).isoformat(),
            correlation_id=str(uuid.uuid4()),
            producer="settlement",
            aggregate_id=user_id,
            payload={"user_id": user_id, "version": version},
        )
        message = aio_pika.Message(
            body=json.dumps(envelope).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=str(event_id),
        )
        await exchange.publish(message, routing_key=routing_key, mandatory=True)
    finally:
        await connection.close()


def _wait_bid(
    client: httpx.Client,
    auction_id: str,
    bidder_id: str,
    amount_cents: int,
    expected_status: int,
    timeout: float = 8,
) -> httpx.Response:
    deadline = time.time() + timeout
    last: httpx.Response | None = None
    while time.time() < deadline:
        last = _bid(
            client,
            auction_id,
            bidder_id,
            amount_cents,
            str(uuid.uuid4()),
        )
        if last.status_code == expected_status:
            return last
        time.sleep(0.1)
    raise AssertionError(
        f"bid status {last.status_code if last is not None else None} "
        f"!= {expected_status}"
    )


@pytest.fixture
def eligibility_consumer() -> Iterator[subprocess.Popen[bytes]]:
    process = _start_eligibility_consumer()
    try:
        yield process
    finally:
        _stop_worker(process)


def test_eligibility_consumer_applies_payment_method_events(
    client: httpx.Client, eligibility_consumer: subprocess.Popen[bytes]
) -> None:
    seller_id = str(uuid.uuid4())
    bidder_id = str(uuid.uuid4())
    auction_id = _create_open_auction(client, seller_id)
    rejected = _bid(client, auction_id, bidder_id, 1100, str(uuid.uuid4()))
    assert rejected.status_code == 403

    ready_event = uuid.uuid4()
    asyncio.run(
        _publish_payment_method(
            event_id=ready_event,
            user_id=bidder_id,
            event_type="PaymentMethodReady",
            version=1,
            routing_key="payment_method.ready.v1",
        )
    )
    accepted = _wait_bid(client, auction_id, bidder_id, 1100, 201)
    assert accepted.status_code == 201

    asyncio.run(
        _publish_payment_method(
            event_id=ready_event,
            user_id=bidder_id,
            event_type="PaymentMethodRemoved",
            version=1,
            routing_key="payment_method.removed.v1",
        )
    )
    still_ready = _wait_bid(client, auction_id, bidder_id, 1200, 201)
    assert still_ready.status_code == 201

    asyncio.run(
        _publish_payment_method(
            event_id=uuid.uuid4(),
            user_id=bidder_id,
            event_type="PaymentMethodRemoved",
            version=0,
            routing_key="payment_method.removed.v1",
        )
    )
    still_ready_after_stale = _wait_bid(client, auction_id, bidder_id, 1300, 201)
    assert still_ready_after_stale.status_code == 201

    asyncio.run(
        _publish_payment_method(
            event_id=uuid.uuid4(),
            user_id=bidder_id,
            event_type="PaymentMethodRemoved",
            version=2,
            routing_key="payment_method.removed.v1",
        )
    )
    removed = _wait_bid(client, auction_id, bidder_id, 1400, 403)
    assert removed.status_code == 403
    assert eligibility_consumer.poll() is None
