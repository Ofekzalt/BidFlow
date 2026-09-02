import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-to-a-long-random-string")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "authentication")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "live-auction-platform")


def register_and_login(client: httpx.Client) -> tuple[str, str]:
    email = f"{uuid4().hex}@example.com"
    password = "password12"
    registered = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert registered.status_code == 201
    user_id = registered.json()["id"]
    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return user_id, login.json()["access_token"]


def auction_body() -> dict:
    now = datetime.now(UTC)
    return {
        "title": "Gateway listing",
        "description": "Created through Kong",
        "starting_price_cents": 1000,
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(days=1)).isoformat(),
    }


def mint_token(*, sub: str, aud: str = JWT_AUDIENCE, secret: str = JWT_SECRET) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "email": "token@example.com",
        "iat": now,
        "exp": now + timedelta(hours=1),
        "iss": JWT_ISSUER,
        "aud": aud,
    }
    return jwt.encode(payload, secret, algorithm="HS256")
