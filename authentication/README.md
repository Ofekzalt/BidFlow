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

Planned public HTTP endpoints:

- `POST /auth/register`
- `POST /auth/login`

JWTs contain the stable user ID in `sub` and are signed only with authentication's RS256 private key. Kong receives the public key only.

## Data ownership

Authentication owns its PostgreSQL database and migration history under `alembic/`. No other service may query this database directly.

## Interacts with

- [`gateway/`](../gateway/README.md) — public route forwarding and public-key verification
- [`frontend/`](../frontend/README.md) — registration and login client
- [`docs/`](../docs/README.md) — contracts and architectural decisions

## Current state

Folder scaffold only. No authentication application, database model, or migration exists yet.
