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

BASE_URL = "http://127.0.0.1:8015"
USER_ID_HEADER = "X-User-Id"


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
                "metadata": {"user_id": fields.get("metadata[user_id]", [""])[0]},
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
        "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
        "STRIPE_API_BASE": stripe_base,
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
            "8015",
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


def test_setup_intent_requires_user(settlement_server: str) -> None:
    response = httpx.post(f"{settlement_server}/payments/setup-intent", timeout=5.0)
    assert response.status_code == 401


def test_lazy_customer_and_off_session_setup(
    settlement_server: str, stripe_stub: tuple[str, type[_StripeHandler]]
) -> None:
    _base, handler = stripe_stub
    user_id = str(uuid.uuid4())
    headers = {USER_ID_HEADER: user_id}

    first = httpx.post(
        f"{settlement_server}/payments/setup-intent",
        headers=headers,
        timeout=5.0,
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["client_secret"]
    customer_id = first_body["stripe_customer_id"]
    assert customer_id.startswith("cus_")

    second = httpx.post(
        f"{settlement_server}/payments/setup-intent",
        headers=headers,
        timeout=5.0,
    )
    assert second.status_code == 200
    assert second.json()["stripe_customer_id"] == customer_id
    assert second.json()["client_secret"] != first_body["client_secret"]

    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT stripe_customer_id FROM stripe_customers WHERE user_id = %s",
                [user_id],
            )
            row = cur.fetchone()
    assert row is not None
    assert row[0] == customer_id

    customer_posts = [
        item for item in handler.log if item[0].startswith("/v1/customers")
    ]
    setup_posts = [
        item for item in handler.log if item[0].startswith("/v1/setup_intents")
    ]
    assert len(customer_posts) == 1
    assert len(setup_posts) == 2
    for _path, fields in setup_posts:
        assert fields.get("usage") == ["off_session"]
        assert fields.get("customer") == [customer_id]
        assert "payment_method_types" not in fields
        assert fields.get("automatic_payment_methods[enabled]") == ["true"]
