# settlement/

The Stripe payment and settlement bounded context.

## Owns

- Lazy Stripe Customer mapping
- SetupIntents configured for future off-session usage
- Saved payment-method state
- Off-session PaymentIntents
- Detailed payment statuses: `PENDING`, `SUCCEEDED`, `FAILED`, `REQUIRES_ACTION`
- Verified Stripe webhook handling
- Payment and webhook idempotency
- In-app payment notifications
- RabbitMQ consumers
- Settlement outbox and publisher
- Settlement PostgreSQL schema, SQLAlchemy models, and Alembic migrations

## Does not own

- User credentials, JWT issuance, or JWT verification
- Auction state, winner selection, or bid acceptance
- Recovery Checkout flows, Stripe Connect, payouts, or live payments

## Event workflow

Produces:

- `PaymentMethodReady`
- `PaymentMethodRemoved`
- `PaymentSucceeded`
- `PaymentFailed`

Consumes:

- `AuctionEnded`

The PaymentIntent response may update internal payment state, but verified Stripe webhooks are the canonical source of final payment events. `REQUIRES_ACTION` remains distinct internally and maps to `PaymentFailed` for the auction workflow because recovery is out of scope.

## Correctness

One logical payment is allowed per auction. Protection layers include consumed-event idempotency, a unique payment-per-auction constraint, Stripe's auction-based idempotency key, and Stripe webhook-event deduplication.

## Identity

Protected routes read the authenticated user id from the Kong-provided `X-User-Id` header. Settlement does not verify JWTs. Missing `X-User-Id` on a protected route returns `401`. Before Kong exists, e2e tests inject `X-User-Id` directly. See [`docs/adr/0002-kong-jwt-edge-identity.md`](../docs/adr/0002-kong-jwt-edge-identity.md).

## Interacts with

- [`auction/`](../auction/README.md) — durable lifecycle and payment-method events
- [`gateway/`](../gateway/README.md) — payment setup routes and public webhook forwarding
- [`frontend/`](../frontend/README.md) — Stripe Elements setup and payment outcome

## Local development

### Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker

### 1. Start Postgres and RabbitMQ

From the repository root:

```bash
docker compose up -d
```

### 2. Configure environment

```bash
cp .env.example .env   # run from settlement/
```

Set `DATABASE_URL`. Set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` to Stripe test values (or the placeholders in `.env.example` when using a local HTTP stub via `STRIPE_API_BASE`). Do not commit live keys.

### 3. Apply migrations

```bash
cd settlement
uv run alembic upgrade head
```

### 4. Run the service

```bash
cd settlement
uv run uvicorn settlement.main:app --host 127.0.0.1 --port 8003 --reload
```

### 5. Run messaging workers

```bash
cd settlement
uv run python -m settlement.workers.outbox_worker
```

```bash
cd settlement
uv run python -m settlement.workers.auction_ended_consumer
```

The outbox worker publishes unpublished outbox rows after broker confirm. The `AuctionEnded` consumer records `processed_events`, creates one payment per auction, and confirms an off-session PaymentIntent. It does not write `PaymentSucceeded` / `PaymentFailed` from the PaymentIntent response.

Webhook requests use `Stripe-Signature` only. Protected payment routes inject `X-User-Id` until Kong exists.

### 6. Run e2e tests

```bash
cd settlement
uv run pytest tests/e2e -v
```

E2e tests start uvicorn on dedicated ports so they do not collide with a local server on `8003`.

## Current state

Lazy Stripe Customer creation, off-session SetupIntents, payment-method attach/remove with outbox events, off-session PaymentIntents on `AuctionEnded`, verified Stripe webhooks, in-app notifications, and `GET /notifications` are implemented. Stripe Elements confirmation remains Phase 7. See [`docs/adr/0005-off-session-paymentintent.md`](../docs/adr/0005-off-session-paymentintent.md) and [`docs/adr/0006-lazy-stripe-customer.md`](../docs/adr/0006-lazy-stripe-customer.md).
