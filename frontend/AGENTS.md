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
- Do not modify backend modules for presentation-only concerns.

## Required verification

Follow root [`AGENTS.md`](../AGENTS.md) testing rules. Run TypeScript type checking and production build. Add browser e2e flows through Kong once the UI exists.
