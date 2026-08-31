import asyncio
import json
import os
import signal
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
from auction.messaging.envelope import build_envelope
from auction.messaging.topology import declare_topology
from tests.conftest import AUCTION_ROOT, DATABASE_URL
from tests.e2e.test_close_worker import _create_open_auction

WINNER_AMOUNT_CENTS = 2500


def _sync_dsn() -> str:
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def _start_payment_result_consumer() -> subprocess.Popen[bytes]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(AUCTION_ROOT / "src"),
        "RABBITMQ_URL": settings.rabbitmq_url,
    }
    return subprocess.Popen(
        ["uv", "run", "python", "-m", "auction.workers.payment_result_consumer"],
        cwd=AUCTION_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )


def _kill_worker_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=5)


def _stop_worker_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def _seed_payment_pending(auction_id: str, winner_id: str) -> None:
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE auctions SET status = 'PAYMENT_PENDING', "
                "winner_id = %s, final_amount_cents = %s WHERE id = %s",
                [winner_id, WINNER_AMOUNT_CENTS, auction_id],
            )
        conn.commit()


def _processed_count(event_id: uuid.UUID) -> int:
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM processed_events WHERE event_id = %s",
                [event_id],
            )
            row = cur.fetchone()
    return int(row[0]) if row is not None else 0


def _wait_blocked_on_processed_events(timeout: float = 30) -> None:
    deadline = time.time() + timeout
    with psycopg.connect(_sync_dsn()) as conn:
        with conn.cursor() as cur:
            while time.time() < deadline:
                cur.execute(
                    """
                    SELECT 1
                    FROM pg_locks blocked
                    JOIN pg_class rel ON rel.oid = blocked.relation
                    WHERE rel.relname = 'processed_events'
                      AND NOT blocked.granted
                    """
                )
                if cur.fetchone() is not None:
                    return
                time.sleep(0.05)
    raise AssertionError("consumer did not wait on processed_events lock")


async def _purge_payment_result_queue() -> None:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await declare_topology(channel, settings.rabbitmq_retry_delays)
        queue = await channel.get_queue("auction.payment-result")
        await queue.purge()
    finally:
        await connection.close()


async def _publish_payment_result(
    *,
    event_id: uuid.UUID,
    auction_id: str,
    event_type: str,
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
            aggregate_id=auction_id,
            payload={"auction_id": auction_id},
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


def _assert_snapshot(body: dict, winner_id: str) -> None:
    assert body["winner_id"] == winner_id
    assert body["final_amount_cents"] == WINNER_AMOUNT_CENTS


@pytest.fixture
def payment_result_consumer() -> Iterator[subprocess.Popen[bytes]]:
    process = _start_payment_result_consumer()
    try:
        yield process
    finally:
        _stop_worker_group(process)


def test_payment_succeeded_and_duplicate_event(
    client: httpx.Client, payment_result_consumer: subprocess.Popen[bytes]
) -> None:
    seller_id = str(uuid.uuid4())
    winner_id = str(uuid.uuid4())
    auction_id = _create_open_auction(client, seller_id)
    _seed_payment_pending(auction_id, winner_id)

    event_id = uuid.uuid4()
    asyncio.run(
        _publish_payment_result(
            event_id=event_id,
            auction_id=auction_id,
            event_type="PaymentSucceeded",
            routing_key="payment.succeeded.v1",
        )
    )
    sold = _wait_status(client, auction_id, "SOLD")
    _assert_snapshot(sold, winner_id)
    assert _processed_count(event_id) == 1

    asyncio.run(
        _publish_payment_result(
            event_id=event_id,
            auction_id=auction_id,
            event_type="PaymentSucceeded",
            routing_key="payment.succeeded.v1",
        )
    )
    time.sleep(0.5)
    duplicate = client.get(f"/auctions/{auction_id}")
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "SOLD"
    _assert_snapshot(duplicate.json(), winner_id)
    assert _processed_count(event_id) == 1


def test_payment_failed_and_late_event_ignored(
    client: httpx.Client, payment_result_consumer: subprocess.Popen[bytes]
) -> None:
    seller_id = str(uuid.uuid4())
    winner_id = str(uuid.uuid4())
    auction_id = _create_open_auction(client, seller_id)
    _seed_payment_pending(auction_id, winner_id)

    failed_event = uuid.uuid4()
    asyncio.run(
        _publish_payment_result(
            event_id=failed_event,
            auction_id=auction_id,
            event_type="PaymentFailed",
            routing_key="payment.failed.v1",
        )
    )
    unpaid = _wait_status(client, auction_id, "UNPAID")
    _assert_snapshot(unpaid, winner_id)

    late_event = uuid.uuid4()
    asyncio.run(
        _publish_payment_result(
            event_id=late_event,
            auction_id=auction_id,
            event_type="PaymentSucceeded",
            routing_key="payment.succeeded.v1",
        )
    )
    deadline = time.time() + 3
    while time.time() < deadline:
        if _processed_count(late_event) == 1:
            break
        time.sleep(0.1)
    assert _processed_count(late_event) == 1
    late = client.get(f"/auctions/{auction_id}")
    assert late.status_code == 200
    assert late.json()["status"] == "UNPAID"
    _assert_snapshot(late.json(), winner_id)


def test_late_failure_does_not_regress_sold(
    client: httpx.Client, payment_result_consumer: subprocess.Popen[bytes]
) -> None:
    seller_id = str(uuid.uuid4())
    winner_id = str(uuid.uuid4())
    auction_id = _create_open_auction(client, seller_id)
    _seed_payment_pending(auction_id, winner_id)

    asyncio.run(
        _publish_payment_result(
            event_id=uuid.uuid4(),
            auction_id=auction_id,
            event_type="PaymentSucceeded",
            routing_key="payment.succeeded.v1",
        )
    )
    _wait_status(client, auction_id, "SOLD")

    asyncio.run(
        _publish_payment_result(
            event_id=uuid.uuid4(),
            auction_id=auction_id,
            event_type="PaymentFailed",
            routing_key="payment.failed.v1",
        )
    )
    time.sleep(0.5)
    sold = client.get(f"/auctions/{auction_id}")
    assert sold.status_code == 200
    assert sold.json()["status"] == "SOLD"
    _assert_snapshot(sold.json(), winner_id)


def test_payment_result_redelivers_when_killed_before_commit(
    client: httpx.Client,
) -> None:
    seller_id = str(uuid.uuid4())
    winner_id = str(uuid.uuid4())
    auction_id = _create_open_auction(client, seller_id)
    _seed_payment_pending(auction_id, winner_id)
    event_id = uuid.uuid4()
    asyncio.run(_purge_payment_result_queue())

    locker = psycopg.connect(_sync_dsn())
    locker.autocommit = False
    locker_cur = locker.cursor()
    locker_cur.execute("LOCK TABLE processed_events IN ACCESS EXCLUSIVE MODE")

    consumer = _start_payment_result_consumer()
    try:
        asyncio.run(
            _publish_payment_result(
                event_id=event_id,
                auction_id=auction_id,
                event_type="PaymentSucceeded",
                routing_key="payment.succeeded.v1",
            )
        )
        _wait_blocked_on_processed_events()
        _kill_worker_group(consumer)
    finally:
        locker.rollback()
        locker_cur.close()
        locker.close()

    assert _processed_count(event_id) == 0
    pending = client.get(f"/auctions/{auction_id}")
    assert pending.status_code == 200
    assert pending.json()["status"] == "PAYMENT_PENDING"

    consumer = _start_payment_result_consumer()
    try:
        sold = _wait_status(client, auction_id, "SOLD")
        _assert_snapshot(sold, winner_id)
        assert _processed_count(event_id) == 1
    finally:
        _stop_worker_group(consumer)
