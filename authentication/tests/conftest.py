import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import psycopg
import pytest

AUTH_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8011"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://authentication:authentication@localhost:5432/authentication",
)
JWT_SECRET = os.environ.get("JWT_SECRET", "authentication-e2e-jwt-secret")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "authentication")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "live-auction-platform")


def _sync_dsn(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture(scope="session")
def auth_server() -> Iterator[str]:
    env = {
        **os.environ,
        "DATABASE_URL": DATABASE_URL,
        "JWT_SECRET": JWT_SECRET,
        "JWT_ISSUER": JWT_ISSUER,
        "JWT_AUDIENCE": JWT_AUDIENCE,
        "PYTHONPATH": str(AUTH_ROOT / "src"),
    }
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "auth.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8011",
        ],
        cwd=AUTH_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            if process.poll() is not None:
                stderr = process.stderr.read().decode() if process.stderr else ""
                raise RuntimeError(f"authentication server exited early: {stderr}")
            try:
                httpx.get(f"{BASE_URL}/docs", timeout=0.5)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            process.kill()
            raise RuntimeError("authentication server did not become ready")
        yield BASE_URL
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(autouse=True)
def clear_users(auth_server: str) -> Iterator[None]:
    with psycopg.connect(_sync_dsn(DATABASE_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE users")
        conn.commit()
    yield


@pytest.fixture
def client(auth_server: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=auth_server, timeout=10.0) as http_client:
        yield http_client
