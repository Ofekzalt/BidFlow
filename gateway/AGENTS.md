# AGENTS.md — gateway

Read [`README.md`](README.md), root [`AGENTS.md`](../AGENTS.md), and the gateway sections of the PRD before editing.

## Agent rules

- Keep gateway configuration declarative and free of business logic.
- Preserve the documented public/protected route list.
- Validate HS256 tokens with `JWT_SECRET`. Never put the secret in the frontend.
- On protected routes, verify JWT signature, issuer, audience, and expiration.
- Strip or overwrite client-supplied `X-User-Id` before forwarding.
- After successful JWT verification, set trusted `X-User-Id` from JWT `sub`.
- Never add credentials capable of issuing tokens.
- Propagate request and correlation IDs.
- Apply bounded retries only to safe idempotent reads.
- Never enable generic POST retries for bid, payment, setup, or webhook routes.
- Keep rate limiting an edge concern without making Redis authoritative business state.
- Do not expose auction, settlement, or authentication service ports publicly in production-style Compose or Kubernetes configuration.
- Do not place environment-specific secrets in tracked configuration.

## Required e2e scenarios

Follow root [`AGENTS.md`](../AGENTS.md) testing rules. Prove these by sending requests through Kong against declarative config:

- Public routing
- Protected-route rejection without JWT
- Valid JWT sets trusted `X-User-Id` downstream
- Client-supplied `X-User-Id` is stripped or overwritten
- Invalid and expired JWT rejection
- Correlation ID propagation
- Rate limits
- Absence of unsafe write retries
