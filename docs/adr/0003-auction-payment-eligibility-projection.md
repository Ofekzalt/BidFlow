# 0003 — Auction payment-eligibility projection with event_id and version

Status: Accepted
Date: 2026-08-25

## Context

Bid acceptance must not call Settlement, Redis, or RabbitMQ while an auction row is locked. Payment readiness still belongs to Settlement. Auction therefore needs a local, eventually consistent projection of whether a bidder may bid.

Duplicate broker delivery and out-of-order delivery are different failures. A unique `event_id` on the one-row-per-user projection only records the last message and cannot ignore a late older event that has a new id. A version-only projection can ignore stale state but does not record that a specific message was already consumed.

## Decision

Auction owns two tables used only for eligibility:

- `processed_events(event_id PK, processed_at)` — set of seen message ids (duplicate delivery)
- `bidder_payment_status(user_id PK, payment_ready, version, updated_at)` — current eligibility; `version` is per user and monotonic in Settlement

`apply_payment_status` runs in one transaction: insert `event_id` (conflict means already seen, skip projection writes); then upsert `bidder_payment_status` only when the incoming `version` is strictly greater than the stored version.

Missing projection row or `payment_ready = false` is not ready. Bid placement reads this table locally and never calls another service.

Bus events remain `PaymentMethodReady` and `PaymentMethodRemoved`. Both map to the same apply with a boolean. The Phase 5 consumer reuses `processed_events` and `apply_payment_status`; it does not add a second id store.

Until that consumer exists, tests seed the projection or call apply against auction PostgreSQL.

## Alternatives

- `source_event_id` on the projection row only: handles identical redelivery poorly once the column is overwritten; does not order distinct events.
- Compare `occurred_at` instead of `version`: clocks and equal timestamps make ordering weaker than an aggregate version.
- Call Settlement during the bid transaction: violates the lock and isolation rules.

## Consequences

- Settlement must emit a unique `event_id` per message and a per-user monotonic payment-status `version`.
- Auction does not own payment-method truth; the projection can lag.
- Unknown eligibility fails closed: the bidder cannot bid.
- A new `event_id` with an older `version` is recorded as processed and does not change `payment_ready`.
