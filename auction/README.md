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

- Credentials or JWT signing
- Stripe customers, payment methods, or PaymentIntents
- Durable event transport configuration outside its own routing contracts
- Authoritative payment-method state

## Correctness boundary

PostgreSQL determines whether a bid succeeds. Bid placement locks the auction row and performs only local database work. It must never call settlement or Redis while holding the lock.

The local `bidder_payment_status` projection is eventually consistent. Unknown or untrusted eligibility fails closed. Settlement remains the source of payment-method truth.

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

## Current state

Folder scaffold only. The auction application and workers are not implemented.
