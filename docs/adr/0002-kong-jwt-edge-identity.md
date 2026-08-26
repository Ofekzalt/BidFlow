# 0002 — Kong as sole JWT verifier with trusted identity forwarding

Status: Accepted
Date: 2026-08-25

## Context

ADR 0001 defines HS256 signing in authentication and verification in Kong. Auction and settlement need the authenticated user id for seller ownership, bidder identity, idempotency scope, and payment setup routes. Services could verify JWTs themselves, but that duplicates Kong, spreads `JWT_SECRET` beyond authentication and Kong, and invites inconsistent validation.

Early scaffolding placed JWT settings in auction. That conflicts with limiting secret distribution to authentication (sign) and Kong (verify).

## Decision

Kong is the only JWT verifier for protected HTTP routes.

Authentication signs access tokens with HS256. See [`0001-hs256-jwt-signing.md`](0001-hs256-jwt-signing.md). Tokens include `sub`, `email`, `iat`, `exp`, `iss`, and `aud`.

Kong verifies JWT signature, issuer, audience, and expiration on protected routes. Public routes do not require a JWT. After successful verification, Kong extracts user identity from `sub` and forwards it to downstream services in `X-User-Id`. Kong must remove or overwrite any client-supplied `X-User-Id` before setting the trusted value.

Auction and settlement do not verify JWTs. They read `X-User-Id` for business authorization: seller ownership, bidder identity, idempotency scope, and similar rules. Protected endpoints return `401` when `X-User-Id` is missing.

Only Kong is externally exposed in production-style Compose and Kubernetes configuration. Auction and settlement are reachable only on the internal network.

Before Kong exists (Phases 2–6), e2e tests for protected endpoints call the service port directly and inject `X-User-Id` explicitly. After Kong exists (Phase 7), protected-route e2e goes through Kong with a Bearer token.

Authentication answers whether a request is authenticated. Kong enforces that at the edge. Auction and settlement answer whether the authenticated user may perform a business action.

## Alternatives

- Each service verifies JWT with `JWT_SECRET`: simpler pre-Kong dev, but duplicates verification and widens secret exposure.
- Trust client-supplied `X-User-Id` without Kong stripping: allows identity spoofing if a service port is reachable directly.

## Consequences

- Auction and settlement settings exclude `JWT_SECRET`, `JWT_ISSUER`, and `JWT_AUDIENCE`.
- Auction and settlement do not depend on PyJWT unless needed for another reason.
- Phase 7 Kong configuration must verify JWTs and strip then set `X-User-Id` on protected routes.
- Pre-Kong tests inject `X-User-Id`; they do not give auction or settlement the JWT secret.
- Client-provided identity headers must never be trusted by downstream services; Kong overwrites them at the edge.
