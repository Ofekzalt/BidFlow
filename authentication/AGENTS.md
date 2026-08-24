# AGENTS.md — authentication

Read [`README.md`](README.md), the root [`AGENTS.md`](../AGENTS.md), and relevant architecture and execution documentation before editing.

## Agent rules

- Keep authentication limited to users, credentials, password hashing, RS256 signing, and JWT issuance.
- Never call Stripe or store Stripe identifiers.
- Never place the RS256 private key in gateway, frontend, Compose values, logs, tests, or Git.
- Keep token claims minimal and versioned through explicit contracts.
- Use SQLAlchemy 2 async and authentication-owned Alembic migrations.
- Never access auction or settlement databases.
- Make registration independent of RabbitMQ, Redis, auction, settlement, and Stripe availability.
- Test password hashing, duplicate email, invalid credentials, JWT signature, issuer, audience, and expiration.
- Do not add roles or authorization features unless the approved requirements demand them.

## Verification

Run authentication unit tests, migration tests from an empty database, Ruff, and the public-route gateway integration test.
