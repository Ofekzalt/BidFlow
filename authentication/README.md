# authentication/

The authentication bounded context for Live Auction Platform.

## Owns

- User registration and login
- Email identity and password hashes
- RS256 private signing key
- JWT issuance and token claims
- Authentication PostgreSQL schema
- Authentication SQLAlchemy models and Alembic migrations

## Does not own

- Stripe customers or payment methods
- Auction authorization rules beyond authenticated identity claims
- Gateway routing or token verification policy
- Other services' user projections

Registration must remain available when Stripe, RabbitMQ, Redis, auction, or settlement is unavailable.

## Interfaces

Public HTTP endpoints (port `8001`):

- `POST /auth/register` — body: `{ "email", "password" }`; returns `201` with id/email/created_at
- `POST /auth/login` — body: `{ "email", "password" }`; returns `200` with RS256 `access_token`

JWTs contain `sub` (user id), `email`, `iat`, `exp`, `iss`, `aud` and are signed only with authentication's RS256 private key. Kong receives the public key only.

## Data ownership

Authentication owns its PostgreSQL database and migration history under `alembic/`. No other service may query this database directly.

## Interacts with

- [`gateway/`](../gateway/README.md) — public route forwarding and public-key verification
- [`frontend/`](../frontend/README.md) — registration and login client
- [`docs/`](../docs/README.md) — contracts and architectural decisions

## Local development

### Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker

### 1. Start Postgres

From the repository root:

```bash
docker compose up -d
```

### 2. Generate RS256 keypair (once)

```bash
mkdir -p authentication/keys
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out authentication/keys/private.pem
openssl rsa -in authentication/keys/private.pem -pubout \
  -out authentication/keys/public.pem
```

`authentication/keys/` is gitignored. Never commit `private.pem`. The public key will be mounted into the gateway in Phase 7.

### 3. Configure environment

```bash
cp .env.example .env   # run from authentication/
```

Edit `DATABASE_URL` and `JWT_PRIVATE_KEY_PATH` to match your local paths.

### 4. Apply migrations

```bash
cd authentication
uv run alembic upgrade head
```

### 5. Run the service

```bash
cd authentication
uv run uvicorn auth.main:app --host 127.0.0.1 --port 8001 --reload
```

## Current state

Application skeleton implemented: settings, async SQLAlchemy session, User model, Alembic migration, RS256 JWT helpers. Register and login routes not yet implemented.
