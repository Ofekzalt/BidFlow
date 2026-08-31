# 0006 — Lazy Stripe Customer on first SetupIntent

Status: Accepted
Date: 2026-08-30

## Context

Settlement needs a Stripe Customer id to attach payment methods and charge winners. Creating that Customer during authentication registration would couple signup to Stripe availability, put Stripe identifiers outside settlement, and create Customers for users who never bid.

## Decision

Authentication registration does not call Stripe. Settlement creates a Stripe Customer on the first `POST /payments/setup-intent` for that user, stores `stripe_customers(user_id → stripe_customer_id)`, and reuses the row on later setup calls.

## Alternatives

- Create the Customer at registration via a cross-service call or shared Stripe key: every user has a Customer immediately, but signup fails when Stripe is down and Stripe leaks into authentication.
- Create the Customer when the first auction opens: still lazy, but sellers who never pay would get Customers and the trigger would sit on the auction path.

## Consequences

- Users with no setup attempt have no Stripe Customer.
- Settlement is the only service that holds Stripe secret configuration.
- SetupIntent is configured with `usage=off_session` so the method can be charged after close.
