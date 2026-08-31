import asyncio
import json
import os
import signal
import subprocess
import threading
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import aio_pika
import psycopg
import pytest

from settlement.messaging.envelope import build_envelope
from settlement.messaging.topology import declare_topology
from tests.conftest import DATABASE_URL, SETTLEMENT_ROOT

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
QUEUE_AUCTION_ENDED = "settlement.auction-ended"


def _sync_dsn(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


class _StripeHandler(BaseHTTPRequestHandler):
    log: list[tuple[str, dict[str, list[str]], str | None]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode()
        fields = parse_qs(raw)
        idempotency = self.headers.get("Idempotency-Key")
        type(self).log.append((self.path, fields, idempotency))
        if self.path.startswith("/v1/payment_intents"):
            intent_id = f"pi_test_{uuid.uuid4().hex}"
            body = {
                "id": intent_id,
                "object": "payment_intent",
                "status": "succeeded",
                "amount": int(fields.get("amount", ["0"])[0]),
                "currency": fields.get("currency", ["usd"])[0],
                "customer": fields.get("customer", [""])[0],
                "payment_method": fields.get("payment_method", [""])[0],
            }
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture
def stripe_stub() -> Iterator[tuple[str, type[_StripeHandler]]]:
    _StripeHandler.log = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StripeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield (f"http://{host}:{port}", _StripeHandler)
    finally:
        server.shutdown()
        thread.join(timeout=5)


def _start_consumer(stripe_base: str) -> subprocess.Popen[bytes]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(SETTLEMENT_ROOT / "src"),
        "RABBITMQ_URL": RABBITMQ_URL,
        "RABBITMQ_RETRY_DELAYS": "0.2,0.2,0.2",
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
        "STRIPE_API_BASE": stripe_base,
    }
    return subprocess.Popen(
        ["uv", "run", "python", "-m", "settlement.workers.auction_ended_consumer"],
        cwd=SETTLEMENT_ROOT,
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


def _stop_worker(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


async def _purge_queue() -> None:
    connection = await aio_pika.connect(RABBITMQ_URL)
    try:
        channel = await connection.channel()
        await declare_topology(channel, "0.2,0.2,0.2")
        queue = await channel.get_queue(QUEUE_AUCTION_ENDED)
        await queue.purge()
    finally:
        await connection.close()


async def _publish_auction_ended(
    event_id: uuid.UUID,
    auction_id: uuid.UUID,
    winner_id: uuid.UUID,
    amount_cents: int = 2500,
) -> None:
    connection = await aio_pika.connect(RABBITMQ_URL)
    try:
        channel = await connection.channel()
        await declare_topology(channel, "0.2,0.2,0.2")
        exchange = await channel.get_exchange("live-auction.events")
        envelope = build_envelope(
            event_id=str(event_id),
            event_type="AuctionEnded",
            event_version="v1",
            occurred_at=datetime.now(UTC).isoformat(),
            correlation_id=str(uuid.uuid4()),
            producer="auction",
            aggregate_id=str(auction_id),
            payload={
                "auction_id": str(auction_id),
                "winner_id": str(winner_id),
                "final_amount_cents": amount_cents,
                "currency": "USD",
                "ended_at": datetime.now(UTC).isoformat(),
            },
        )
        message = aio_pika.Message(
            body=json.dumps(envelope).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=str(event_id),
        )
        await exchange.publish(message, routing_key="auction.ended.v1", mandatory=True)
    finally:
        await connection.close()


def _seed_default_method(user_id: uuid.UUID) -> tuple[str, str]:
    customer_id = f"cus_test_{uuid.uuid4().hex}"
    payment_method_id = f"pm_card_{uuid.uuid4().hex}"
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO stripe_customers (user_id, stripe_customer_id)
                VALUES (%s, %s)
                """,
                [user_id, customer_id],
            )
            cur.execute(
                """
                INSERT INTO payment_methods (
                    id, user_id, stripe_payment_method_id, is_default
                )
                VALUES (%s, %s, %s, TRUE)
                """,
                [uuid.uuid4(), user_id, payment_method_id],
            )
        conn.commit()
    return customer_id, payment_method_id


def _processed_event_count(event_id: uuid.UUID) -> int:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM processed_events WHERE event_id = %s",
                [event_id],
            )
            row = cur.fetchone()
    return int(row[0]) if row is not None else 0


def _wait_blocked_on_processed_events(timeout: float = 30) -> None:
    deadline = time.time() + timeout
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
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


def _payments(auction_id: uuid.UUID) -> list[tuple[object, ...]]:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT auction_id, winner_id, amount_cents, currency, status,
                       stripe_payment_intent_id
                FROM payments
                WHERE auction_id = %s
                """,
                [auction_id],
            )
            return list(cur.fetchall())


def _wait_payment(
    auction_id: uuid.UUID, status: str, timeout: float = 8
) -> tuple[object, ...]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = _payments(auction_id)
        if rows and rows[0][4] == status:
            return rows[0]
        time.sleep(0.1)
    raise AssertionError("payment row was not written")


def _outbox_types(auction_id: uuid.UUID) -> list[str]:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_type FROM outbox_events
                WHERE aggregate_id = %s
                  AND event_type IN ('PaymentSucceeded', 'PaymentFailed')
                ORDER BY created_at
                """,
                [auction_id],
            )
            return [row[0] for row in cur.fetchall()]


@pytest.fixture(autouse=True)
def settlement_tables(settlement_schema: None) -> Iterator[None]:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                TRUNCATE TABLE payments, payment_methods, stripe_customers,
                    outbox_events, processed_events, notifications
                """
            )
        conn.commit()
    yield


@pytest.fixture
def consumer(
    stripe_stub: tuple[str, type[_StripeHandler]],
) -> Iterator[tuple[subprocess.Popen[bytes], type[_StripeHandler]]]:
    stripe_base, handler = stripe_stub
    asyncio.run(_purge_queue())
    process = _start_consumer(stripe_base)
    try:
        yield process, handler
    finally:
        _stop_worker(process)


def test_ten_duplicate_auction_ended_one_payment(
    consumer: tuple[subprocess.Popen[bytes], type[_StripeHandler]],
) -> None:
    _process, handler = consumer
    winner_id = uuid.uuid4()
    auction_id = uuid.uuid4()
    customer_id, payment_method_id = _seed_default_method(winner_id)
    event_id = uuid.uuid4()
    for _ in range(10):
        asyncio.run(_publish_auction_ended(event_id, auction_id, winner_id))
    row = _wait_payment(auction_id, "SUCCEEDED")
    assert len(_payments(auction_id)) == 1
    assert row[0] == auction_id
    assert row[1] == winner_id
    assert row[2] == 2500
    assert row[3] == "USD"
    assert row[4] == "SUCCEEDED"
    assert row[5] is not None
    pi_posts = [
        item for item in handler.log if item[0].startswith("/v1/payment_intents")
    ]
    assert len(pi_posts) == 1
    _path, fields, idempotency = pi_posts[0]
    assert idempotency == f"auction:{auction_id}"
    assert fields.get("customer") == [customer_id]
    assert fields.get("payment_method") == [payment_method_id]
    assert fields.get("confirm") == ["true"]
    assert fields.get("off_session") == ["true"]
    assert "payment_method_types" not in fields
    assert fields.get("automatic_payment_methods[allow_redirects]") == ["never"]
    assert _outbox_types(auction_id) == []


def test_different_event_ids_same_auction_one_payment(
    consumer: tuple[subprocess.Popen[bytes], type[_StripeHandler]],
) -> None:
    _process, handler = consumer
    winner_id = uuid.uuid4()
    auction_id = uuid.uuid4()
    _seed_default_method(winner_id)
    asyncio.run(_publish_auction_ended(uuid.uuid4(), auction_id, winner_id))
    _wait_payment(auction_id, "SUCCEEDED")
    asyncio.run(_publish_auction_ended(uuid.uuid4(), auction_id, winner_id))
    time.sleep(1.0)
    assert len(_payments(auction_id)) == 1
    pi_posts = [
        item for item in handler.log if item[0].startswith("/v1/payment_intents")
    ]
    assert len(pi_posts) == 1
    assert _outbox_types(auction_id) == []


def test_missing_payment_method_fails_without_stripe_charge(
    consumer: tuple[subprocess.Popen[bytes], type[_StripeHandler]],
) -> None:
    _process, handler = consumer
    winner_id = uuid.uuid4()
    auction_id = uuid.uuid4()
    asyncio.run(_publish_auction_ended(uuid.uuid4(), auction_id, winner_id, 1800))
    row = _wait_payment(auction_id, "FAILED")
    assert row[4] == "FAILED"
    assert row[5] is None
    pi_posts = [
        item for item in handler.log if item[0].startswith("/v1/payment_intents")
    ]
    assert pi_posts == []
    assert _outbox_types(auction_id) == ["PaymentFailed"]
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT type, payload FROM notifications WHERE user_id = %s",
                [winner_id],
            )
            notes = cur.fetchall()
    assert len(notes) == 1
    assert notes[0][0] == "PaymentFailed"
    assert notes[0][1]["auction_id"] == str(auction_id)
    asyncio.run(_publish_auction_ended(uuid.uuid4(), auction_id, winner_id, 1800))
    time.sleep(1.0)
    assert _outbox_types(auction_id) == ["PaymentFailed"]
    assert len(_payments(auction_id)) == 1


def test_auction_ended_redelivers_when_killed_before_commit(
    stripe_stub: tuple[str, type[_StripeHandler]],
) -> None:
    stripe_base, _handler = stripe_stub
    winner_id = uuid.uuid4()
    auction_id = uuid.uuid4()
    event_id = uuid.uuid4()
    _seed_default_method(winner_id)
    asyncio.run(_purge_queue())

    locker = psycopg.connect(_sync_dsn(DATABASE_URL))
    locker.autocommit = False
    locker_cur = locker.cursor()
    locker_cur.execute("LOCK TABLE processed_events IN ACCESS EXCLUSIVE MODE")

    consumer = _start_consumer(stripe_base)
    try:
        asyncio.run(_publish_auction_ended(event_id, auction_id, winner_id))
        _wait_blocked_on_processed_events()
        _kill_worker_group(consumer)
    finally:
        locker.rollback()
        locker_cur.close()
        locker.close()

    assert _processed_event_count(event_id) == 0
    assert _payments(auction_id) == []

    consumer = _start_consumer(stripe_base)
    try:
        row = _wait_payment(auction_id, "SUCCEEDED")
        assert row[4] == "SUCCEEDED"
        assert _processed_event_count(event_id) == 1
    finally:
        _stop_worker(consumer)
