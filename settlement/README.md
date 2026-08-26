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

## Current state

Folder scaffold only. No Stripe or settlement behavior is implemented.
