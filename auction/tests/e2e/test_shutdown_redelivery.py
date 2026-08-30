import asyncio
import os
import signal
import subprocess
import time
import uuid

import aio_pika
import httpx
import psycopg

from auction.config.settings import settings
from auction.messaging.topology import declare_topology
from tests.conftest import AUCTION_ROOT, DATABASE_URL
from tests.e2e.test_bidding import _bid, _create_open_auction
from tests.e2e.test_eligibility_consumer import _publish_payment_method, _wait_bid


def _sync_dsn() -> str:
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


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


def _processed_event_count(event_id: uuid.UUID) -> int:
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


async def _purge_payment_method_queue() -> None:
    connection = await aio_pika.connect(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await declare_topology(channel, settings.rabbitmq_retry_delays)
        queue = await channel.get_queue("auction.payment-method")
        await queue.purge()
    finally:
        await connection.close()


def test_eligibility_consumer_redelivers_when_killed_before_commit(
    client: httpx.Client,
) -> None:
    seller_id = str(uuid.uuid4())
    bidder_id = str(uuid.uuid4())
    auction_id = _create_open_auction(client, seller_id)
    rejected = _bid(client, auction_id, bidder_id, 1100, str(uuid.uuid4()))
    assert rejected.status_code == 403
    asyncio.run(_purge_payment_method_queue())

    ready_event = uuid.uuid4()
    locker = psycopg.connect(_sync_dsn())
    locker.autocommit = False
    locker_cur = locker.cursor()
    locker_cur.execute("LOCK TABLE processed_events IN ACCESS EXCLUSIVE MODE")

    consumer = _start_eligibility_consumer()
    try:
        asyncio.run(
            _publish_payment_method(
                event_id=ready_event,
                user_id=bidder_id,
                event_type="PaymentMethodReady",
                version=1,
                routing_key="payment_method.ready.v1",
            )
        )
        _wait_blocked_on_processed_events()
        _kill_worker_group(consumer)
    finally:
        locker.rollback()
        locker_cur.close()
        locker.close()

    assert _processed_event_count(ready_event) == 0
    still_rejected = _bid(client, auction_id, bidder_id, 1100, str(uuid.uuid4()))
    assert still_rejected.status_code == 403

    consumer = _start_eligibility_consumer()
    try:
        accepted = _wait_bid(client, auction_id, bidder_id, 1100, 201)
        assert accepted.status_code == 201
        assert _processed_event_count(ready_event) == 1
    finally:
        _stop_worker_group(consumer)
