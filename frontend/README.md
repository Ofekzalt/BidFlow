# frontend/

The user-facing React, Vite, and TypeScript browser application.

## Owns

- Registration and login UI
- Auction list, detail, creation, and bidding UI
- Stripe Elements payment-method setup
- Notifications and payment-outcome presentation
- Client-side state and routing
- Non-sensitive browser configuration
- Frontend tests, package manifest, and lockfile

## Does not own

- Authoritative auction, bid, payment, or authentication rules
- Direct access to backend databases, RabbitMQ, Redis, or Stripe secret APIs
- Gateway routing policy
- Deployment infrastructure or backend configuration
- Secrets of any kind

## API boundary

The browser calls only [`gateway/`](../gateway/README.md). It does not call backend service ports directly.

Initial auction updates use polling every one or two seconds. WebSockets are optional and may be added only after core correctness is complete. A real-time notification tells the client to refresh authoritative state; it does not become business truth.

## Security

Browser bundles are public. Never include `JWT_SECRET`, Stripe secret keys, webhook secrets, database credentials, or privileged service URLs. Stripe Elements uses only the publishable key.

## Interacts with

- [`gateway/`](../gateway/README.md) — sole backend entry point
- [`authentication/`](../authentication/README.md) — registration/login through gateway
- [`auction/`](../auction/README.md) — auction and bidding APIs through gateway
- [`settlement/`](../settlement/README.md) — Stripe setup and notifications through gateway

## Current state

Folder scaffold only. No Vite application or package manifest exists yet.
