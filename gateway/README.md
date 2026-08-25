# gateway/

Kong OSS edge-gateway configuration.

## Owns

- Client-to-service routing
- Public and protected route policy
- HS256 JWT verification using `JWT_SECRET`
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

## Retry boundary

Safe GET requests may use bounded gateway retries. Bid and payment writes rely on application-level idempotency and are not retried generically by Kong.

## Key ownership

Gateway verifies HS256 tokens with `JWT_SECRET`. Do not commit the secret or place it in the frontend. See [`docs/adr/0001-hs256-jwt-signing.md`](../docs/adr/0001-hs256-jwt-signing.md).

## Current state

Folder scaffold only. Kong configuration is not implemented.
