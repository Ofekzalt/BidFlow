# 0005 — Off-session PaymentIntent for winner charges

Status: Accepted
Date: 2026-08-30

## Context

When an auction closes with a winner, settlement must charge a previously saved payment method without the bidder present. Stripe Checkout could collect payment on a hosted page, but that would require the winner to return after close and would mix a recovery UI into the close path. Recovery Checkout is out of scope for this phase.

The immediate PaymentIntent API response can report `succeeded` or `requires_action`. Treating that response as the domain outcome would duplicate or race Stripe webhooks, which are the canonical source of final payment events.

## Decision

Settlement creates and confirms a PaymentIntent with `confirm=true`, `off_session=true`, and `automatic_payment_methods` enabled. The Stripe idempotency key is `auction:{auction_id}`. Internal payment status may become `PENDING`, `SUCCEEDED`, `FAILED`, or `REQUIRES_ACTION` from the API response. `PaymentSucceeded` and `PaymentFailed` outbox events are written only from verified, deduplicated webhooks (or when no saved method exists, so no PaymentIntent is created). `REQUIRES_ACTION` stays distinct internally and maps to `PaymentFailed` for auction because recovery is out of scope.

## Alternatives

- Stripe Checkout after close: clearer for SCA recovery, but the winner must complete a hosted session and the close path would wait on a browser.
- Emit domain events from the PaymentIntent response: faster auction updates, but duplicate webhooks and immediate success would double-emit or race.

## Consequences

- Auction never calls Stripe. Settlement owns all PaymentIntent traffic.
- SCA and other `requires_action` outcomes look like unpaid auctions until a later recovery product exists.
- Webhook signature verification and `stripe_webhook_events` dedupe are required for a single result event.
- The `AuctionEnded` consumer now charges; it is no longer the processed-events-only consumer described as a Phase 6 leftover in [`0004-transactional-outbox-and-retry-headers.md`](0004-transactional-outbox-and-retry-headers.md).
