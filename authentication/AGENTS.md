# AGENTS.md — authentication

Read [`README.md`](README.md), the root [`AGENTS.md`](../AGENTS.md), and relevant architecture and execution documentation before editing.

## Agent rules

- Keep authentication limited to users, credentials, password hashing, HS256 signing, and JWT issuance.
- Never call Stripe or store Stripe identifiers.
- Never commit `JWT_SECRET` or put it in the frontend or logs.
- Keep token claims minimal and versioned through explicit contracts.
- Use SQLAlchemy 2 async and authentication-owned Alembic migrations.
- Never access auction or settlement databases.
- Make registration independent of RabbitMQ, Redis, auction, settlement, and Stripe availability.
- Do not add roles or authorization features unless the approved requirements demand them.

## Required e2e scenarios

Follow root [`AGENTS.md`](../AGENTS.md) testing rules. Prove these through HTTP against the authentication service port until Kong exists, then through Kong:

- Register returns 201 with id, email, and created_at; email stored lowercased
- Duplicate email returns 409
- Login returns 200 with HS256 access_token; claims include sub, email, iss, aud, exp
- Invalid credentials return 401 with the same message for unknown email and wrong password
- Short password returns 422

## Verification

Run authentication e2e tests against the service port until Kong exists (then through Kong), Alembic upgrade from an empty database, and Ruff.
