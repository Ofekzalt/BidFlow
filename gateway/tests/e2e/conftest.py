import os
from collections.abc import Iterator

import httpx
import psycopg
import pytest

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8080")
AUTH_DSN = os.environ.get(
    "AUTH_DSN",
    "postgresql://authentication:authentication@localhost:5432/authentication",
)
AUCTION_DSN = os.environ.get(
    "AUCTION_DSN",
    "postgresql://auction:auction@localhost:5432/auction",
)


@pytest.fixture(scope="session")
def gateway_url() -> str:
    with httpx.Client(base_url=GATEWAY_URL, timeout=5.0) as client:
        response = client.get("/auctions")
        response.raise_for_status()
    return GATEWAY_URL


@pytest.fixture(autouse=True)
def clear_tables(gateway_url: str) -> Iterator[None]:
    with psycopg.connect(AUTH_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE users")
        conn.commit()
    with psycopg.connect(AUCTION_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE auctions, bidder_payment_status, "
                "processed_events, bids, idempotency_keys, outbox_events"
            )
        conn.commit()
    yield


@pytest.fixture
def client(gateway_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=gateway_url, timeout=10.0) as http_client:
        yield http_client
