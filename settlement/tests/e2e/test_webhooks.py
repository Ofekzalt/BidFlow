import hashlib
import hmac
import json
import os
import subprocess
import time
import uuid
from collections.abc import Iterator

import httpx
import psycopg
import pytest

from tests.conftest import DATABASE_URL, SETTLEMENT_ROOT

BASE_URL = "http://127.0.0.1:8017"
USER_ID_HEADER = "X-User-Id"
WEBHOOK_SECRET = "whsec_test_webhooks"


def _sync_dsn(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


def _sign(payload: bytes) -> str:
    timestamp = str(int(time.time()))
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _pi_event(
    event_type: str,
    payment_intent_id: str,
    status: str,
    *,
    event_id: str | None = None,
) -> bytes:
    event = {
        "id": event_id or f"evt_{uuid.uuid4().hex}",
        "object": "event",
        "type": event_type,
        "data": {
            "object": {
                "id": payment_intent_id,
                "object": "payment_intent",
                "status": status,
            }
        },
    }
    return json.dumps(event, separators=(",", ":")).encode()


def _seed_payment(
    *,
    auction_id: uuid.UUID,
    winner_id: uuid.UUID,
    payment_intent_id: str | None,
    status: str = "PENDING",
) -> None:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payments (
                    id, auction_id, winner_id, amount_cents, currency,
                    stripe_payment_intent_id, status
                )
                VALUES (%s, %s, %s, 2500, 'USD', %s, %s)
                """,
                [uuid.uuid4(), auction_id, winner_id, payment_intent_id, status],
            )
        conn.commit()


def _outbox(auction_id: uuid.UUID) -> list[tuple[str, dict[str, object]]]:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_type, payload FROM outbox_events
                WHERE aggregate_id = %s
                  AND event_type IN ('PaymentSucceeded', 'PaymentFailed')
                ORDER BY created_at
                """,
                [auction_id],
            )
            return [(row[0], row[1]) for row in cur.fetchall()]


def _payment_status(auction_id: uuid.UUID) -> str | None:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM payments WHERE auction_id = %s",
                [auction_id],
            )
            row = cur.fetchone()
    return str(row[0]) if row else None


def _webhook_event_count() -> int:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM stripe_webhook_events")
            row = cur.fetchone()
    return int(row[0]) if row else 0


def _post_webhook(server: str, payload: bytes, signature: str | None) -> httpx.Response:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if signature is not None:
        headers["Stripe-Signature"] = signature
    return httpx.post(
        f"{server}/webhooks/stripe",
        content=payload,
        headers=headers,
        timeout=5.0,
    )


@pytest.fixture(autouse=True)
def settlement_tables(settlement_schema: None) -> Iterator[None]:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                TRUNCATE TABLE payments, notifications, stripe_webhook_events,
                    outbox_events, processed_events
                """
            )
        conn.commit()
    yield


@pytest.fixture
def settlement_server(settlement_schema: None) -> Iterator[str]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(SETTLEMENT_ROOT / "src"),
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_WEBHOOK_SECRET": WEBHOOK_SECRET,
    }
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "settlement.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8017",
        ],
        cwd=SETTLEMENT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            if process.poll() is not None:
                stderr = process.stderr.read().decode() if process.stderr else ""
                raise RuntimeError(f"settlement server exited early: {stderr}")
            try:
                httpx.get(f"{BASE_URL}/docs", timeout=0.5)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            process.kill()
            raise RuntimeError("settlement server did not become ready")
        yield BASE_URL
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_webhook_rejects_bad_signature(settlement_server: str) -> None:
    auction_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    pi_id = f"pi_{uuid.uuid4().hex}"
    _seed_payment(auction_id=auction_id, winner_id=winner_id, payment_intent_id=pi_id)
    payload = _pi_event("payment_intent.succeeded", pi_id, "succeeded")
    missing = _post_webhook(settlement_server, payload, None)
    assert missing.status_code == 400
    bad = _post_webhook(settlement_server, payload, "t=1,v1=deadbeef")
    assert bad.status_code == 400
    assert _webhook_event_count() == 0
    assert _outbox(auction_id) == []
    assert _payment_status(auction_id) == "PENDING"


def test_webhook_success_failure_requires_action_and_replay(
    settlement_server: str,
) -> None:
    winner_id = uuid.uuid4()
    headers = {USER_ID_HEADER: str(winner_id)}
    unauthorized = httpx.get(f"{settlement_server}/notifications", timeout=5.0)
    assert unauthorized.status_code == 401

    auction_id = uuid.uuid4()
    pi_id = f"pi_{uuid.uuid4().hex}"
    _seed_payment(auction_id=auction_id, winner_id=winner_id, payment_intent_id=pi_id)
    event_id = f"evt_{uuid.uuid4().hex}"
    payload = _pi_event(
        "payment_intent.succeeded", pi_id, "succeeded", event_id=event_id
    )
    ok = _post_webhook(settlement_server, payload, _sign(payload))
    assert ok.status_code == 200
    assert _payment_status(auction_id) == "SUCCEEDED"
    rows = _outbox(auction_id)
    assert [row[0] for row in rows] == ["PaymentSucceeded"]
    assert rows[0][1]["auction_id"] == str(auction_id)

    listed = httpx.get(
        f"{settlement_server}/notifications", headers=headers, timeout=5.0
    )
    assert listed.status_code == 200
    notes = listed.json()
    assert len(notes) == 1
    assert notes[0]["type"] == "PaymentSucceeded"
    assert notes[0]["payload"]["auction_id"] == str(auction_id)

    replay = _post_webhook(settlement_server, payload, _sign(payload))
    assert replay.status_code == 200
    assert _outbox(auction_id) == rows
    assert (
        len(
            httpx.get(
                f"{settlement_server}/notifications", headers=headers, timeout=5.0
            ).json()
        )
        == 1
    )

    failed_auction = uuid.uuid4()
    failed_pi = f"pi_{uuid.uuid4().hex}"
    _seed_payment(
        auction_id=failed_auction, winner_id=winner_id, payment_intent_id=failed_pi
    )
    fail_payload = _pi_event(
        "payment_intent.payment_failed", failed_pi, "requires_payment_method"
    )
    failed = _post_webhook(settlement_server, fail_payload, _sign(fail_payload))
    assert failed.status_code == 200
    assert _payment_status(failed_auction) == "FAILED"
    assert [row[0] for row in _outbox(failed_auction)] == ["PaymentFailed"]

    action_auction = uuid.uuid4()
    action_pi = f"pi_{uuid.uuid4().hex}"
    _seed_payment(
        auction_id=action_auction, winner_id=winner_id, payment_intent_id=action_pi
    )
    action_payload = _pi_event(
        "payment_intent.requires_action", action_pi, "requires_action"
    )
    action = _post_webhook(settlement_server, action_payload, _sign(action_payload))
    assert action.status_code == 200
    assert _payment_status(action_auction) == "REQUIRES_ACTION"
    assert [row[0] for row in _outbox(action_auction)] == ["PaymentFailed"]


def test_webhook_emits_one_result_after_immediate_pi_success(
    settlement_server: str,
) -> None:
    auction_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    pi_id = f"pi_{uuid.uuid4().hex}"
    _seed_payment(
        auction_id=auction_id,
        winner_id=winner_id,
        payment_intent_id=pi_id,
        status="SUCCEEDED",
    )
    assert _outbox(auction_id) == []
    payload = _pi_event("payment_intent.succeeded", pi_id, "succeeded")
    assert _post_webhook(settlement_server, payload, _sign(payload)).status_code == 200
    assert _payment_status(auction_id) == "SUCCEEDED"
    assert [row[0] for row in _outbox(auction_id)] == ["PaymentSucceeded"]
    second = _pi_event("payment_intent.succeeded", pi_id, "succeeded")
    assert _post_webhook(settlement_server, second, _sign(second)).status_code == 200
    assert [row[0] for row in _outbox(auction_id)] == ["PaymentSucceeded"]


def test_webhook_before_payment_intent_id_is_not_swallowed(
    settlement_server: str,
) -> None:
    auction_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    pi_id = f"pi_{uuid.uuid4().hex}"
    _seed_payment(
        auction_id=auction_id,
        winner_id=winner_id,
        payment_intent_id=None,
    )
    event_id = f"evt_{uuid.uuid4().hex}"
    payload = _pi_event(
        "payment_intent.succeeded", pi_id, "succeeded", event_id=event_id
    )
    early = _post_webhook(settlement_server, payload, _sign(payload))
    assert early.status_code == 503
    assert _webhook_event_count() == 0
    assert _outbox(auction_id) == []
    assert _payment_status(auction_id) == "PENDING"

    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE payments SET stripe_payment_intent_id = %s "
                "WHERE auction_id = %s",
                [pi_id, auction_id],
            )
        conn.commit()

    later = _post_webhook(settlement_server, payload, _sign(payload))
    assert later.status_code == 200
    assert _webhook_event_count() == 1
    assert _payment_status(auction_id) == "SUCCEEDED"
    assert [row[0] for row in _outbox(auction_id)] == ["PaymentSucceeded"]


def test_later_webhook_does_not_overwrite_result(settlement_server: str) -> None:
    winner_id = uuid.uuid4()
    succeeded_auction = uuid.uuid4()
    succeeded_pi = f"pi_{uuid.uuid4().hex}"
    _seed_payment(
        auction_id=succeeded_auction,
        winner_id=winner_id,
        payment_intent_id=succeeded_pi,
    )
    success_payload = _pi_event("payment_intent.succeeded", succeeded_pi, "succeeded")
    assert (
        _post_webhook(
            settlement_server, success_payload, _sign(success_payload)
        ).status_code
        == 200
    )
    fail_after = _pi_event(
        "payment_intent.payment_failed", succeeded_pi, "requires_payment_method"
    )
    assert (
        _post_webhook(settlement_server, fail_after, _sign(fail_after)).status_code
        == 200
    )
    assert _payment_status(succeeded_auction) == "SUCCEEDED"
    assert [row[0] for row in _outbox(succeeded_auction)] == ["PaymentSucceeded"]

    failed_auction = uuid.uuid4()
    failed_pi = f"pi_{uuid.uuid4().hex}"
    _seed_payment(
        auction_id=failed_auction,
        winner_id=winner_id,
        payment_intent_id=failed_pi,
    )
    fail_payload = _pi_event(
        "payment_intent.payment_failed", failed_pi, "requires_payment_method"
    )
    assert (
        _post_webhook(settlement_server, fail_payload, _sign(fail_payload)).status_code
        == 200
    )
    success_after = _pi_event("payment_intent.succeeded", failed_pi, "succeeded")
    assert (
        _post_webhook(
            settlement_server, success_after, _sign(success_after)
        ).status_code
        == 200
    )
    assert _payment_status(failed_auction) == "FAILED"
    assert [row[0] for row in _outbox(failed_auction)] == ["PaymentFailed"]
