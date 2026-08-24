# AGENTS.md — gateway

Read [`README.md`](README.md), root [`AGENTS.md`](../AGENTS.md), and the gateway sections of the PRD before editing.

## Agent rules

- Keep gateway configuration declarative and free of business logic.
- Preserve the documented public/protected route list.
- Validate RS256 tokens with the public key only.
- Never add credentials capable of issuing tokens.
- Propagate request and correlation IDs.
- Apply bounded retries only to safe idempotent reads.
- Never enable generic POST retries for bid, payment, setup, or webhook routes.
- Keep rate limiting an edge concern without making Redis authoritative business state.
- Do not expose service ports or internal administrative endpoints publicly.
- Do not place environment-specific secrets in tracked configuration.

## Required verification

Test public routing, protected-route rejection, valid JWT forwarding, invalid/expired JWT rejection, correlation IDs, rate limits, and absence of unsafe write retries.
