# AGENTS.md — settlement

Read [`README.md`](README.md), root [`AGENTS.md`](../AGENTS.md), and the settlement sections of the PRD and implementation plan before editing.

## Agent rules

- Keep every Stripe concern inside settlement.
- Create Stripe Customers lazily; authentication registration must not depend on Stripe.
- Use SQLAlchemy 2 async and settlement-owned Alembic migrations.
- Configure saved methods for future off-session use.
- Enforce one logical payment per auction in PostgreSQL.
- Use Stripe idempotency key `auction:{auction_id}`.
- Preserve detailed internal payment status.
- Emit final payment events only from verified, deduplicated webhooks.
- Never emit a final event from the immediate PaymentIntent response.
- Publish payment-method projection events through the transactional outbox.
- Keep domain-event bodies immutable; retry state belongs in RabbitMQ headers.
- ACK only after database commit.
- On shutdown, stop consuming/claiming and finish or safely roll back in-flight work.
- Use explicit Stripe timeouts and bounded retries only where idempotency makes them safe.
- Never log Stripe secrets, payment-method details, webhook secrets, or sensitive payloads.

## Required tests

- Lazy Customer creation and reuse
- SetupIntent off-session configuration
- Ten duplicate `AuctionEnded` events create one logical payment
- Invalid and duplicate webhooks
- Immediate success plus webhook emits one final event
- Decline and `REQUIRES_ACTION` mapping
- Payment-method ready/removed outbox events
- ACK-after-commit and shutdown redelivery
