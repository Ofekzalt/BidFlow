import hashlib
import hmac
import json
import os
import subprocess
import threading
import time
import uuid
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import httpx
import psycopg
import pytest

from tests.conftest import DATABASE_URL, SETTLEMENT_ROOT

BASE_URL = "http://127.0.0.1:8016"
USER_ID_HEADER = "X-User-Id"
WEBHOOK_SECRET = "whsec_test_settlement"


def _sync_dsn(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


class _StripeHandler(BaseHTTPRequestHandler):
    log: list[tuple[str, dict[str, list[str]]]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode()
        fields = parse_qs(raw)
        type(self).log.append((self.path, fields))
        if self.path.startswith("/v1/customers"):
            body = {
                "id": f"cus_test_{uuid.uuid4().hex}",
                "object": "customer",
            }
        elif self.path.startswith("/v1/setup_intents"):
            customer = fields.get("customer", [""])[0]
            intent_id = f"seti_test_{uuid.uuid4().hex}"
            body = {
                "id": intent_id,
                "object": "setup_intent",
                "client_secret": f"{intent_id}_secret_x",
                "customer": customer,
                "usage": fields.get("usage", [""])[0],
            }
        elif "/detach" in self.path:
            pm_id = self.path.split("/")[3]
            body = {"id": pm_id, "object": "payment_method", "customer": None}
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


def _sign(payload: bytes) -> str:
    timestamp = str(int(time.time()))
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _attached_event(customer_id: str, payment_method_id: str) -> bytes:
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "object": "event",
        "type": "payment_method.attached",
        "data": {
            "object": {
                "id": payment_method_id,
                "object": "payment_method",
                "customer": customer_id,
            }
        },
    }
    return json.dumps(event, separators=(",", ":")).encode()


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


@pytest.fixture
def settlement_server(
    settlement_schema: None, stripe_stub: tuple[str, type[_StripeHandler]]
) -> Iterator[str]:
    stripe_base, _handler = stripe_stub
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(SETTLEMENT_ROOT / "src"),
        "STRIPE_SECRET_KEY": "sk_test_placeholder",
        "STRIPE_API_BASE": stripe_base,
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
            "8016",
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


def _create_customer(server: str, user_id: str) -> str:
    response = httpx.post(
        f"{server}/payments/setup-intent",
        headers={USER_ID_HEADER: user_id},
        timeout=5.0,
    )
    assert response.status_code == 200
    return str(response.json()["stripe_customer_id"])


def _outbox_rows(user_id: str) -> list[tuple[str, dict[str, object], object]]:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_type, payload, published_at
                FROM outbox_events
                WHERE aggregate_id = %s
                  AND event_type IN ('PaymentMethodReady', 'PaymentMethodRemoved')
                ORDER BY created_at
                """,
                [user_id],
            )
            return [(row[0], row[1], row[2]) for row in cur.fetchall()]


def test_methods_require_user(settlement_server: str) -> None:
    listed = httpx.get(f"{settlement_server}/payments/methods", timeout=5.0)
    assert listed.status_code == 401
    deleted = httpx.delete(
        f"{settlement_server}/payments/methods/{uuid.uuid4()}", timeout=5.0
    )
    assert deleted.status_code == 401


def test_attach_and_remove_payment_method(settlement_server: str) -> None:
    user_id = str(uuid.uuid4())
    headers = {USER_ID_HEADER: user_id}
    customer_id = _create_customer(settlement_server, user_id)

    empty = httpx.get(
        f"{settlement_server}/payments/methods", headers=headers, timeout=5.0
    )
    assert empty.status_code == 200
    assert empty.json() == []

    payment_method_id = f"pm_card_{uuid.uuid4().hex}"
    payload = _attached_event(customer_id, payment_method_id)
    webhook = httpx.post(
        f"{settlement_server}/webhooks/stripe",
        content=payload,
        headers={
            "Stripe-Signature": _sign(payload),
            "Content-Type": "application/json",
        },
        timeout=5.0,
    )
    assert webhook.status_code == 200

    listed = httpx.get(
        f"{settlement_server}/payments/methods", headers=headers, timeout=5.0
    )
    assert listed.status_code == 200
    methods = listed.json()
    assert len(methods) == 1
    assert methods[0]["stripe_payment_method_id"] == payment_method_id
    assert methods[0]["is_default"] is True
    assert "number" not in methods[0]
    assert "cvc" not in methods[0]
    method_id = methods[0]["id"]

    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT stripe_payment_method_id, is_default
                FROM payment_methods
                WHERE user_id = %s
                """,
                [user_id],
            )
            row = cur.fetchone()
    assert row == (payment_method_id, True)

    ready_rows = _outbox_rows(user_id)
    assert len(ready_rows) == 1
    event_type, event_payload, published_at = ready_rows[0]
    assert event_type == "PaymentMethodReady"
    assert published_at is None
    assert event_payload["user_id"] == user_id
    assert event_payload["version"] == 1

    removed = httpx.delete(
        f"{settlement_server}/payments/methods/{method_id}",
        headers=headers,
        timeout=5.0,
    )
    assert removed.status_code == 204

    after_delete = httpx.get(
        f"{settlement_server}/payments/methods", headers=headers, timeout=5.0
    )
    assert after_delete.status_code == 200
    assert after_delete.json() == []

    outbox = _outbox_rows(user_id)
    assert [row[0] for row in outbox] == ["PaymentMethodReady", "PaymentMethodRemoved"]
    assert outbox[1][1]["user_id"] == user_id
    assert outbox[1][1]["version"] == 2
    assert outbox[1][2] is None

    second_pm = f"pm_card_{uuid.uuid4().hex}"
    second_payload = _attached_event(customer_id, second_pm)
    second_webhook = httpx.post(
        f"{settlement_server}/webhooks/stripe",
        content=second_payload,
        headers={
            "Stripe-Signature": _sign(second_payload),
            "Content-Type": "application/json",
        },
        timeout=5.0,
    )
    assert second_webhook.status_code == 200
    versions = [row[1]["version"] for row in _outbox_rows(user_id)]
    assert versions == [1, 2, 3]
    assert _outbox_rows(user_id)[2][0] == "PaymentMethodReady"


def test_second_attached_method_is_sole_default(settlement_server: str) -> None:
    user_id = str(uuid.uuid4())
    headers = {USER_ID_HEADER: user_id}
    customer_id = _create_customer(settlement_server, user_id)
    first_pm = f"pm_card_{uuid.uuid4().hex}"
    second_pm = f"pm_card_{uuid.uuid4().hex}"
    for payment_method_id in (first_pm, second_pm):
        payload = _attached_event(customer_id, payment_method_id)
        webhook = httpx.post(
            f"{settlement_server}/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": _sign(payload),
                "Content-Type": "application/json",
            },
            timeout=5.0,
        )
        assert webhook.status_code == 200

    listed = httpx.get(
        f"{settlement_server}/payments/methods", headers=headers, timeout=5.0
    )
    assert listed.status_code == 200
    methods = listed.json()
    assert len(methods) == 2
    defaults = [item for item in methods if item["is_default"] is True]
    assert len(defaults) == 1
    assert defaults[0]["stripe_payment_method_id"] == second_pm
