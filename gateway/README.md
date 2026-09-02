# gateway/

Kong OSS edge-gateway configuration.

## Owns

- Client-to-service routing
- Public and protected route policy
- HS256 JWT verification using `JWT_SECRET`
- Trusted identity forwarding via `X-User-Id` from JWT `sub`
- Correlation/request ID propagation
- Rate limiting
- Bounded retries for explicitly safe idempotent reads
- Gateway-local declarative configuration

## Does not own

- Authentication credentials or JWT signing
- Business authorization rules
- Auction, bid, or payment logic
- Generic retries for unsafe writes
- Service database access

## Route policy

Public:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auctions`
- `GET /auctions/{id}`
- `GET /auctions/{id}/current-bid`
- `POST /webhooks/stripe`, authenticated by Stripe signature in settlement

Everything else is protected unless an approved requirement explicitly says otherwise.

## JWT and identity forwarding

On protected routes Kong verifies JWT signature, issuer, audience, and expiration using `JWT_SECRET`. Missing, invalid, or expired tokens are rejected before the request reaches a downstream service.

After successful verification, Kong extracts user identity from JWT `sub` and forwards it in `X-User-Id`. Kong must remove or overwrite any client-supplied `X-User-Id` before setting the trusted value. Client-provided identity headers must never be trusted.

Downstream services do not verify JWTs. They read `X-User-Id` for business authorization and return `401` when the header is missing on protected routes. See [`docs/adr/0002-kong-jwt-edge-identity.md`](../docs/adr/0002-kong-jwt-edge-identity.md).

## Network exposure

Only Kong is externally exposed in production-style Compose and Kubernetes configuration. Auction, settlement, and authentication service ports are reachable only on the internal network.

## Retry boundary

Safe GET requests may use bounded gateway retries. Bid and payment writes rely on application-level idempotency and are not retried generically by Kong.

## Key ownership

Gateway verifies HS256 tokens with `JWT_SECRET`. Do not commit the secret or place it in the frontend. See [`docs/adr/0001-hs256-jwt-signing.md`](../docs/adr/0001-hs256-jwt-signing.md).

## Rate limiting

Global, in-memory (`policy: local`), **30 requests per second** and **200 per minute** per client IP. Redis is not used. Compose runs Kong with a single worker so local counters are not split across processes.

## Current state

Declarative Kong 3.9 config in [`kong.yml`](kong.yml) is wired through Docker Compose. The proxy is published at `http://localhost:8080`. Authentication, auction, and settlement listen only on the Compose network.

`JWT_SECRET` is injected at container start from the environment (see [`.env.example`](../.env.example)). It is not stored as a real secret in git.

Gateway e2e: from `gateway/`, `uv run pytest tests/e2e -v` against a running Compose stack (and `docker compose -f docker-compose.retry.yml up -d` for retry tests on port 8081).
