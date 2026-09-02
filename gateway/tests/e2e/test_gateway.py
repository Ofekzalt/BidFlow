import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from tests.e2e.helpers import (
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_SECRET,
    auction_body,
    mint_token,
    register_and_login,
)


def test_public_register_and_list_auctions(client) -> None:
    email = f"{uuid4().hex}@example.com"
    registered = client.post(
        "/auth/register",
        json={"email": email, "password": "password12"},
    )
    assert registered.status_code == 201
    listed = client.get("/auctions")
    assert listed.status_code == 200
    assert listed.json() == []


def test_protected_bid_route_rejects_missing_jwt(client) -> None:
    response = client.post("/auctions", json=auction_body())
    assert response.status_code == 401


def test_valid_jwt_forwards_trusted_user_id(client) -> None:
    user_id, token = register_and_login(client)
    created = client.post(
        "/auctions",
        headers={"Authorization": f"Bearer {token}"},
        json=auction_body(),
    )
    assert created.status_code == 201
    assert created.json()["seller_id"] == user_id


def test_client_supplied_user_id_is_overwritten(client) -> None:
    user_id, token = register_and_login(client)
    spoofed = str(uuid4())
    created = client.post(
        "/auctions",
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-Id": spoofed,
        },
        json=auction_body(),
    )
    assert created.status_code == 201
    assert created.json()["seller_id"] == user_id
    assert created.json()["seller_id"] != spoofed


def test_invalid_jwt_is_rejected(client) -> None:
    token = mint_token(sub=str(uuid4()), secret="not-the-gateway-secret")
    response = client.post(
        "/auctions",
        headers={"Authorization": f"Bearer {token}"},
        json=auction_body(),
    )
    assert response.status_code == 401


def test_expired_jwt_is_rejected(client) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "email": "expired@example.com",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    response = client.post(
        "/auctions",
        headers={"Authorization": f"Bearer {token}"},
        json=auction_body(),
    )
    assert response.status_code == 401


def test_wrong_audience_is_rejected(client) -> None:
    user_id, _ = register_and_login(client)
    token = mint_token(sub=user_id, aud="not-the-platform")
    response = client.post(
        "/auctions",
        headers={"Authorization": f"Bearer {token}"},
        json=auction_body(),
    )
    assert response.status_code == 401


def test_correlation_ids_are_generated_and_echoed(client) -> None:
    generated = client.get("/auctions")
    assert generated.status_code == 200
    request_id = generated.headers.get("X-Request-Id")
    correlation_id = generated.headers.get("X-Correlation-Id")
    assert request_id
    assert correlation_id
    assert request_id == correlation_id

    echoed = client.get("/auctions", headers={"X-Request-Id": "client-request-1"})
    assert echoed.status_code == 200
    assert echoed.headers.get("X-Request-Id") == "client-request-1"
    assert echoed.headers.get("X-Correlation-Id") == "client-request-1"


def test_rate_limit_returns_429(client) -> None:
    time.sleep(1.1)

    def ping() -> int:
        return client.get("/auctions").status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        statuses = list(pool.map(lambda _: ping(), range(80)))
    assert 429 in statuses
