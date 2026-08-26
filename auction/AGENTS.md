# AGENTS.md — auction

Read [`README.md`](README.md), root [`AGENTS.md`](../AGENTS.md), approved auction rules, and relevant execution documentation before editing.

## Agent rules

- Preserve auction and bidding as one transactional bounded context.
- Use SQLAlchemy 2 async and auction-owned Alembic migrations.
- Use integer cents and timezone-aware UTC.
- Bid acceptance must lock the auction row and use PostgreSQL-authoritative state.
- Never call settlement, Redis, Stripe, or another remote dependency while holding an auction lock.
- Payment eligibility comes from the local idempotent projection; unknown eligibility rejects the bid.
- Scope bid idempotency by `(user_id, endpoint, key)` and reject request-hash mismatch with `409`.
- Closing uses bounded ordered batches and PostgreSQL claiming safe for multiple replicas.
- Snapshot `winner_id` and `final_amount_cents` when bidding ends; later payment failure must not alter them.
- Apply payment results only with conditional `PAYMENT_PENDING` transitions.
- Write state and outbox rows in the same transaction.
- Consumers ACK only after commit and safely nack/rollback on failure.
- Workers stop new claims during shutdown and finish or roll back in-flight work.
- Redis is optional and must not affect correctness.
- Read authenticated user id from trusted `X-User-Id`; do not verify JWTs or hold `JWT_SECRET`.
- Return `401` when `X-User-Id` is missing on protected routes.
- Before Kong exists, e2e tests inject `X-User-Id` on the service port; after Phase 7, protected-route e2e goes through Kong.

## Required e2e scenarios

Follow root [`AGENTS.md`](../AGENTS.md) testing rules. Prove these against the auction service port with injected `X-User-Id` until Kong exists, then through Kong. Use the real app, auction PostgreSQL, and messaging fixtures:

- Concurrent bids with no lost update
- Fifty duplicate idempotent requests create one bid
- Seller, late, stale, and ineligible bids are rejected
- Duplicate and out-of-order projection events
- Multi-replica close worker
- Duplicate and late payment-result events
- RabbitMQ outage with outbox recovery
