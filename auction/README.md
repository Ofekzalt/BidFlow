# auction/

The auction bounded context, including auction listings and bidding.

Auction and bidding intentionally share one service because bid acceptance must atomically validate auction state, seller identity, end time, current price, and payment eligibility before updating the winner.

## Owns

- Auction listings and lifecycle
- Bids and bid idempotency
- Current winner and current price
- Immutable winner/final-price snapshots after bidding ends
- PostgreSQL concurrency control
- Local bidder-payment-eligibility projection
- Auction close worker
- Payment-result and eligibility-event consumers
- Auction outbox and publisher
- Auction PostgreSQL schema, SQLAlchemy models, and Alembic migrations

## Does not own

- Credentials, JWT signing, or JWT verification
- Stripe customers, payment methods, or PaymentIntents
- Durable event transport configuration outside its own routing contracts
- Authoritative payment-method state

## Correctness boundary

PostgreSQL determines whether a bid succeeds. Bid placement locks the auction row and performs only local database work. It must never call settlement or Redis while holding the lock.

The local `bidder_payment_status` projection is eventually consistent. Unknown or untrusted eligibility fails closed. Settlement remains the source of payment-method truth.

## Identity

Protected routes read the authenticated user id from the Kong-provided `X-User-Id` header. Auction does not verify JWTs. Missing `X-User-Id` on a protected route returns `401`. Before Kong exists, e2e tests inject `X-User-Id` directly. See [`docs/adr/0002-kong-jwt-edge-identity.md`](../docs/adr/0002-kong-jwt-edge-identity.md).

## Lifecycle

```text
DRAFT → OPEN
OPEN → UNSOLD
OPEN → PAYMENT_PENDING
PAYMENT_PENDING → SOLD
PAYMENT_PENDING → UNPAID
```

Late payment events cannot change `SOLD` to `UNPAID` or `UNPAID` to `SOLD`.

## Events

Produces:

- `AuctionEnded` for winner-bearing auctions

Consumes:

- `PaymentMethodReady`
- `PaymentMethodRemoved`
- `PaymentSucceeded`
- `PaymentFailed`

`BidPlaced` is not a required cross-service event without a concrete consumer.

## Interacts with

- [`gateway/`](../gateway/README.md) — HTTP routing and authentication
- [`settlement/`](../settlement/README.md) — asynchronous payment and eligibility events
- [`frontend/`](../frontend/README.md) — auction browsing, creation, and bidding

## Interfaces

HTTP endpoints (port `8002`):

- `POST /auctions` — seller creates `DRAFT`; requires `X-User-Id`
- `PATCH /auctions/{id}` — seller only, `DRAFT` only
- `POST /auctions/{id}/open` — seller opens `DRAFT → OPEN`
- `POST /auctions/{id}/bids` — bidder places a bid; requires `X-User-Id` and `Idempotency-Key`
- `GET /auctions`, `GET /auctions/{id}`, `GET /auctions/{id}/current-bid` — public reads

Money is integer cents. `starting_price_cents` must be greater than 0. `start_time` must be before `end_time`. Bid `amount_cents` must be greater than `current_price_cents`. Missing `X-User-Id` on writes returns `401`. Non-seller writes and ineligible bidders return `403`. Edits after `OPEN`, bids after close or on a non-open auction, and idempotency key reuse with a different body return `409`.

Payment eligibility is the local `bidder_payment_status` projection. Unknown or `payment_ready=false` rejects the bid. Until Phase 5, seed that table (or call `apply_payment_status`) in tests. See [`docs/adr/0003-auction-payment-eligibility-projection.md`](../docs/adr/0003-auction-payment-eligibility-projection.md).

## Data ownership

Auction owns its PostgreSQL database and migration history under `alembic/`. No other service may query this database directly.

## Local development

### Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker

### 1. Start Postgres

From the repository root:

```bash
docker compose up -d
```

### 2. Configure environment

```bash
cp .env.example .env   # run from auction/
```

Set `DATABASE_URL`.

### 3. Apply migrations

```bash
cd auction
uv run alembic upgrade head
```

### 4. Run the service

```bash
cd auction
uv run uvicorn auction.main:app --host 127.0.0.1 --port 8002 --reload
```

Protected writes need `X-User-Id` until Kong exists (Phase 7).

### 5. Run e2e tests

```bash
cd auction
uv run pytest tests/e2e -v
```

E2e tests start uvicorn on port `8013` so they do not collide with a local server on `8002`.

Example bid (auction must be `OPEN`; bidder must have `payment_ready=true` in `bidder_payment_status`):

```bash
curl -sS -X POST "http://127.0.0.1:8002/auctions/$AUCTION_ID/bids" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $BIDDER_ID" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"amount_cents":1100}'
```

## Current state

Phase 3 bidding and the local payment-eligibility projection are implemented: `POST /auctions/{id}/bids` with row locking and `Idempotency-Key`, `apply_payment_status` / `is_payment_ready`, and fail-closed eligibility. Close worker and RabbitMQ consumers are not implemented.
