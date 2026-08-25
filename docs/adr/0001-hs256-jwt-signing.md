# 0001 — HS256 JWT signing with a shared secret

Status: Accepted
Date: 2026-08-25

## Context

Authentication issued JWTs with RS256 using a private key file. Local setup required generating and wiring a PEM keypair. The operator asked to sign with HS256 so a secret can be set in the authentication environment file.

RS256 lets the gateway verify tokens with a public key that cannot mint tokens. HS256 uses one shared secret for both signing and verification.

## Decision

Authentication signs access tokens with HS256 using `JWT_SECRET` from environment configuration. Only authentication mints tokens. Kong verifies tokens with the same secret using HS256 and validates `iss` and `aud`.

Access tokens include `sub`, `email`, `iat`, `exp`, `iss`, and `aud`. Defaults: `JWT_ISSUER=authentication`, `JWT_AUDIENCE=live-auction-platform`.

## Alternatives

- Keep RS256 and document key generation: stronger key isolation, more local setup.
- HS256 with a file-backed secret: still a shared secret, extra file path.

## Consequences

- Authentication configuration uses `JWT_SECRET`, `JWT_ISSUER`, and `JWT_AUDIENCE` instead of `JWT_PRIVATE_KEY_PATH`.
- Kong receives `JWT_SECRET` at runtime for verification only. Wire it through Compose or deployment environment variables; do not commit it, place it in the frontend, or store it in tracked gateway configuration.
- Authentication and Kong must use the same `JWT_SECRET`, `JWT_ISSUER`, and `JWT_AUDIENCE` values.
- Any process that holds `JWT_SECRET` can mint valid tokens. Limit distribution to authentication for signing and Kong for verification.
- Rotate the secret by changing `JWT_SECRET` and invalidating outstanding tokens.
