import os
import socket
import subprocess
import time
from collections.abc import Iterator

import httpx
import psycopg
import pytest

from tests.conftest import DATABASE_URL, SETTLEMENT_ROOT

BASE_URL = "http://127.0.0.1:8014"
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "127.0.0.1")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "5672"))


def _sync_dsn(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture(scope="session")
def settlement_server(settlement_schema: None) -> Iterator[str]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(SETTLEMENT_ROOT / "src"),
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
            "8014",
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


def test_settlement_shell(settlement_server: str) -> None:
    response = httpx.get(f"{settlement_server}/docs", timeout=5.0)
    assert response.status_code == 200

    dsn = _sync_dsn(DATABASE_URL)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('outbox_events', 'processed_events')
                ORDER BY table_name
                """
            )
            tables = [row[0] for row in cur.fetchall()]
    assert tables == ["outbox_events", "processed_events"]

    with socket.create_connection((RABBITMQ_HOST, RABBITMQ_PORT), timeout=2) as sock:
        sock.sendall(b"AMQP\x00\x00\x09\x01")
        greeting = sock.recv(8)
    assert greeting
