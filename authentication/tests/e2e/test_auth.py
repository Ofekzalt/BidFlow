import jwt

from auth.constants import (
    ERROR_EMAIL_ALREADY_REGISTERED,
    ERROR_INVALID_CREDENTIALS,
    JWT_ALGORITHM,
    JWT_CLAIM_AUD,
    JWT_CLAIM_EMAIL,
    JWT_CLAIM_EXP,
    JWT_CLAIM_IAT,
    JWT_CLAIM_ISS,
    JWT_CLAIM_SUB,
)
from tests.conftest import JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET


def test_register_login_and_credential_rules(client) -> None:
    email = "Alex@Example.com"
    password = "password12"

    short = client.post("/auth/register", json={"email": email, "password": "short"})
    assert short.status_code == 422

    created = client.post("/auth/register", json={"email": email, "password": password})
    assert created.status_code == 201
    body = created.json()
    assert body["email"] == "alex@example.com"
    assert body["id"]
    assert body["created_at"]

    duplicate = client.post(
        "/auth/register", json={"email": "alex@example.com", "password": password}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == ERROR_EMAIL_ALREADY_REGISTERED

    login = client.post(
        "/auth/login", json={"email": "ALEX@example.com", "password": password}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    header = jwt.get_unverified_header(token)
    assert header["alg"] == JWT_ALGORITHM
    claims = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
    )
    assert claims[JWT_CLAIM_SUB] == body["id"]
    assert claims[JWT_CLAIM_EMAIL] == "alex@example.com"
    assert claims[JWT_CLAIM_ISS] == JWT_ISSUER
    assert claims[JWT_CLAIM_AUD] == JWT_AUDIENCE
    assert JWT_CLAIM_EXP in claims
    assert JWT_CLAIM_IAT in claims

    unknown = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": password},
    )
    wrong = client.post(
        "/auth/login",
        json={"email": "alex@example.com", "password": "wrong-password"},
    )
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["detail"] == ERROR_INVALID_CREDENTIALS
    assert wrong.json()["detail"] == ERROR_INVALID_CREDENTIALS
