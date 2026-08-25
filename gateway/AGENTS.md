# AGENTS.md — gateway

Read [`README.md`](README.md), root [`AGENTS.md`](../AGENTS.md), and the gateway sections of the PRD before editing.

## Agent rules

- Keep gateway configuration declarative and free of business logic.
- Preserve the documented public/protected route list.
- Validate HS256 tokens with `JWT_SECRET`. Never put the secret in the frontend.
- Never add credentials capable of issuing tokens.
- Propagate request and correlation IDs.
- Apply bounded retries only to safe idempotent reads.
- Never enable generic POST retries for bid, payment, setup, or webhook routes.
- Keep rate limiting an edge concern without making Redis authoritative business state.
- Do not expose service ports or internal administrative endpoints publicly.
- Do not place environment-specific secrets in tracked configuration.

## Required e2e scenarios

Follow root [`AGENTS.md`](../AGENTS.md) testing rules. Prove these by sending requests through Kong against declarative config:

- Public routing
- Protected-route rejection
- Valid JWT forwarding
- Invalid and expired JWT rejection
- Correlation ID propagation
- Rate limits
- Absence of unsafe write retries
