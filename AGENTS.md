# AGENTS.md

Instructions for AI agents working in this repository. This is the authoritative agent document for repository-wide work.

## What this repository is

Live Auction Platform is a portfolio-grade monorepo for a timed English-auction system. It contains three FastAPI services, a React client, Kong gateway configuration, local runtime orchestration, documentation, and CI automation.

The repository is in early scaffolding. Architecture documentation describes approved intent, not implemented behavior. Do not describe planned behavior as implemented.

## Modules

| Path | Owns |
| --- | --- |
| [`authentication/`](authentication/README.md) | Registration, credentials, HS256 signing, and JWT issuance |
| [`auction/`](auction/README.md) | Auctions, bids, concurrency, lifecycle workers, local projections, and auction events |
| [`settlement/`](settlement/README.md) | Stripe customers, payment methods, payments, webhooks, notifications, and settlement events |
| [`frontend/`](frontend/README.md) | React, Vite, and TypeScript browser client |
| [`gateway/`](gateway/README.md) | Kong edge routing, JWT verification, rate limiting, and safe read retries |
| [`docs/`](docs/README.md) | PRD, implementation plan, architecture knowledge, and ADRs |
| [`.github/`](.github/AUTOMATION.md) | Repository governance and CI automation |

## Required reading

Before changing a module:

1. Read its `README.md`.
2. Read its `AGENTS.md`.
3. Read the relevant architecture and execution documentation.
4. Read related ADRs under [`docs/adr/`](docs/adr/).

## Architectural rules

- PostgreSQL is authoritative business state.
- Each backend service owns its database, SQLAlchemy models, and Alembic migration history.
- Never read or write another service's database.
- Auction bid decisions are local PostgreSQL transactions. Never call settlement while holding an auction lock.
- RabbitMQ carries durable business events. Redis is optional cache or ephemeral infrastructure.
- Redis failure must not permit invalid bids, block otherwise valid authoritative bids, or duplicate payments.
- Stripe state belongs only to settlement.
- Authentication signs JWTs with HS256 using `JWT_SECRET`. Do not commit the secret or put it in the frontend. See [`docs/adr/0001-hs256-jwt-signing.md`](docs/adr/0001-hs256-jwt-signing.md).
- Stripe webhooks are the canonical source of final payment events.
- Consumers ACK only after their database transaction commits.
- Workers stop claiming new work on shutdown and finish or safely roll back in-flight work.
- Unsafe writes are not retried unless their idempotency semantics explicitly permit it.
- Money uses integer cents. Timestamps use timezone-aware UTC.
- Never add a distributed-system pattern without a concrete requirement and consumer.

## Testing

Prove behavior through the running stack, not isolated helpers. Keep coverage small: one e2e test per meaningful contract or failure mode.

**E2e only:** HTTP against real PostgreSQL, the real service process, and Kong for API routes.

**Platform e2e (later):** browser flows through Kong once the frontend exists.

**Workers and consumers:** run the real worker entrypoint with real PostgreSQL and messaging fixtures; still e2e, not isolated helpers.

**TDD:** write a failing e2e test for the user-visible contract, then implement.

**Forbidden:** unit tests; integration tests (`TestClient`, `ASGITransport`, in-process ASGI); mocking the owned database; changing tests to match broken behavior; tests that only assert mocks were called.

Module `AGENTS.md` files list required e2e scenarios for their bounded context.

## Change rules

- Keep changes small and traceable to the request.
- Do not refactor, rename, reformat, or clean adjacent code without instruction.
- Do not add code comments.
- Write a failing e2e test before implementation for features and bug fixes.
- Do not change an existing test merely to make it pass.
- Add migrations for schema changes; never edit an already-applied migration.
- Do not introduce cross-module imports. Communicate through HTTP contracts or versioned events.
- Do not add WebSockets, Redis caching, AI, tracing, Keycloak, Stripe Connect, or cloud deployment before the required core work is complete.

## Architecture decisions

Do not make architectural decisions silently. If the PRD or an existing ADR does not resolve a meaningful trade-off, stop and surface it. Once decided, record it under [`docs/adr/`](docs/adr/).

## Secrets and configuration

- Never commit passwords, private keys, Stripe keys, webhook secrets, tokens, or credential-bearing URLs.
- Commit only examples and secret references.
- Services receive runtime configuration through explicit environment variables and typed settings.
- Runtime and deployment definitions may wire settings but do not own business defaults.

## Pull requests

All pull requests must follow [`.github/pull_request_template.md`](.github/pull_request_template.md). Explain cross-module changes, include verification evidence, and identify any ADR or migration.

## Where to look

- [`README.md`](README.md) — repository purpose and boundaries
- Module `README.md` and `AGENTS.md` files — local ownership and agent instructions
- [`docs/`](docs/README.md) — architecture and execution knowledge
- [`docs/adr/`](docs/adr/) — architectural decisions
