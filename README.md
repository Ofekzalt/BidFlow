## At a glance (for reviewers)

**What:** Live timed-auction platform — microservices, event-driven messaging, Stripe settlement.

**Stack:** Python, FastAPI, PostgreSQL, RabbitMQ, Kong, Stripe, Docker, React.

**Try it locally (≈5 min):**

```bash
git clone https://github.com/Ofekzalt/BidFlow.git && cd BidFlow
cp .env.example .env
docker compose up -d
```

| Service     | URL (local)                          |
|-------------|--------------------------------------|
| API gateway | http://localhost:8080                |
| RabbitMQ UI | http://localhost:15672 (guest/guest) |

**Architecture (one screen):**

```text
[React] → [Kong :8080] → auth | auction | settlement
                              ↓         ↓
                         PostgreSQL   RabbitMQ → workers (outbox, idempotent handlers)
                              ↓
                         Stripe webhooks (deduplicated)
```

**What to look at:** `docker-compose.yml`, `auction/`, `settlement/`, `docs/`, per-service READMEs.

**Author:** Ofek Zaltman — [LinkedIn](https://www.linkedin.com/in/ofek-zaltman) · [GitHub](https://github.com/Ofekzalt)

---

# Live Auction Platform

An event-driven timed English-auction platform built to demonstrate defensible backend architecture, transactional correctness, failure recovery, observability, and local Kubernetes operations.

This repository is a monorepo containing the complete source and local operational definition of one distributed application.

## System thesis

Three backend services own distinct business capabilities:

```text
Kong gateway
├── authentication  → users, credentials, HS256 JWTs
├── auction         → listings, bids, concurrency, lifecycle
└── settlement      → Stripe payment methods, payments, webhooks

PostgreSQL → authoritative state and transactional correctness
RabbitMQ   → durable asynchronous business communication
Redis      → optional cache and ephemeral infrastructure
Stripe     → external payment provider in test mode
```

Auction and bidding intentionally share one service and database because placing a bid must atomically validate auction state and update the current winner. Settlement publishes payment-method eligibility events so bidding remains local and never waits on a network call while holding an auction row lock.

## Modules

| Path | Owns |
| --- | --- |
| [`authentication/`](authentication/README.md) | Registration, password hashing, HS256 signing, JWT issuance |
| [`auction/`](auction/README.md) | Auctions, bids, lifecycle, PostgreSQL concurrency, local projections, workers |
| [`settlement/`](settlement/README.md) | Stripe setup, PaymentIntents, webhooks, payment state, notifications |
| [`frontend/`](frontend/README.md) | React, Vite, and TypeScript browser application |
| [`gateway/`](gateway/README.md) | Kong routes, public/protected policy, JWT validation, rate limiting |
| [`docs/`](docs/README.md) | Product requirements, plans, architecture, and ADRs |
| [`.github/`](.github/AUTOMATION.md) | Pull-request governance and CI automation |

## Core guarantees

- PostgreSQL, not Redis, decides whether a bid succeeds.
- Concurrent bids are serialized with PostgreSQL row-level concurrency control.
- Schema ownership follows service ownership; each service has independent Alembic migrations.
- Domain changes and outbox events commit in one transaction.
- RabbitMQ consumers are idempotent and ACK only after database commit.
- Payment completion comes from verified, deduplicated Stripe webhooks.
- Late payment events cannot regress terminal auction state.
- Redis may improve performance but is never required for correctness.

## Intended runtime

Development starts with Docker Compose. Once the application works and its correctness tests pass, Helm deploys it to kind or minikube. There is no cloud deployment in v1.

Planned infrastructure:

| System | Role |
| --- | --- |
| PostgreSQL | Separate authoritative database per backend service |
| RabbitMQ | Durable events, retry queues, and DLQ |
| Redis | Optional read caching, rate-limit backing, future ephemeral fan-out |
| Stripe test mode | SetupIntent, saved payment methods, off-session PaymentIntent, webhooks |
| Prometheus and Grafana | Domain and reliability metrics |
| Kong OSS | Edge gateway |

## Local setup

```bash
docker compose up -d
```

Postgres initialises the three service databases automatically on first start via [`scripts/init-databases.sql`](scripts/init-databases.sql).

Copy `.env.example` to `.env` and fill in values before starting any service.

## Current state

Services, Docker Compose, and module-level documentation are in active development. See each module README and `docs/` for implementation status and ADRs.

## Working in this repository

Read [`AGENTS.md`](AGENTS.md) before making changes, then read the target module's `README.md` and `AGENTS.md`. Record significant decisions under [`docs/adr/`](docs/adr/) and use [the pull request template](.github/pull_request_template.md).
