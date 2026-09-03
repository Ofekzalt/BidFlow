# 0007 — Browser JWT storage in localStorage

Status: Accepted
Date: 2026-09-03

## Context

Phase 7 needs a browser client that sends `Authorization: Bearer` to Kong on protected routes. The PRD and existing ADRs define how tokens are signed and verified, but not where the browser keeps the access token between page loads.

Options include in-memory storage, `sessionStorage`, `localStorage`, and HttpOnly cookies. HttpOnly cookies would require additional gateway or authentication changes beyond the current Kong JWT-at-edge model.

## Decision

The React client stores the access token in `localStorage` under `bidflow.access_token`.

On sign-in, the client saves the token returned by `POST /auth/login`. On load, it reads the token, rejects expired tokens using the JWT `exp` claim, and attaches the token to gateway requests through the shared HTTP client. Sign-out clears the stored token.

## Alternatives

- In-memory only: safer against XSS exfiltration, but every refresh logs the user out during demos.
- `sessionStorage`: survives reload within one tab, cleared when the tab closes; slightly narrower XSS exposure window than `localStorage`.
- HttpOnly cookie: better XSS resistance, but needs cookie issuance and CORS/credentials changes not planned for Phase 7.

## Consequences

- XSS in the frontend bundle can read the token. This is acceptable for a local portfolio demo; do not treat browser storage as a high-assurance session mechanism.
- Token lifetime follows authentication service defaults (currently one hour). There is no refresh endpoint; expired tokens require signing in again.
- `JWT_SECRET` must never enter the frontend bundle. Only the access token itself is stored client-side.
