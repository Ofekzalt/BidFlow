import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import psycopg
import pytest

AUCTION_ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "http://127.0.0.1:8013"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://auction:auction@localhost:5432/auction",
)


def _sync_dsn(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture(scope="session")
def auction_server() -> Iterator[str]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "PYTHONPATH": str(AUCTION_ROOT / "src"),
    }
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "auction.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8013",
        ],
        cwd=AUCTION_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            if process.poll() is not None:
                stderr = process.stderr.read().decode() if process.stderr else ""
                raise RuntimeError(f"auction server exited early: {stderr}")
            try:
                httpx.get(f"{BASE_URL}/docs", timeout=0.5)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            process.kill()
            raise RuntimeError("auction server did not become ready")
        yield BASE_URL
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(autouse=True)
def clear_auctions(auction_server: str) -> Iterator[None]:
    dsn = _sync_dsn(DATABASE_URL)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE auctions, bidder_payment_status, "
                "processed_events, bids, idempotency_keys, outbox_events"
            )
        conn.commit()
    yield


@pytest.fixture
def client(auction_server: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=auction_server, timeout=10.0) as http_client:
        yield http_client
