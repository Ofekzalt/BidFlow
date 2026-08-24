# AGENTS.md — frontend

Read [`README.md`](README.md), root [`AGENTS.md`](../AGENTS.md), and relevant user stories before editing.

## Agent rules

- Use React, Vite, and TypeScript.
- Call backend APIs only through the configured gateway base URL.
- Keep authoritative business validation in backend services; frontend validation is user guidance only.
- Use Stripe Elements with a publishable key only.
- Never expose secrets or privileged internal service addresses.
- Poll auction reads every one or two seconds initially.
- Do not add WebSockets or Redis Pub/Sub before all core acceptance criteria pass.
- Handle explicit backend error codes for stale bids, idempotency conflicts, closed auctions, and missing payment eligibility.
- Keep components focused; do not add a design-system abstraction for one use.
- Add frontend tests for changed behavior and run type checking/build verification.
- Do not modify backend modules for presentation-only concerns.

## Required verification

Run frontend tests, TypeScript type checking, production build, and the gateway-only integration flow.
