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

Vite React TypeScript app with CSS Modules, Base UI primitives, TanStack Query, Zod DTOs, and axios. The browser calls Kong at `VITE_API_BASE_URL` (default `http://localhost:8080`). Stripe Elements uses only `VITE_STRIPE_PUBLISHABLE_KEY`.

Implemented screens: register/login, auction list and detail (1.5s polling, server-derived countdown), bid form, draft create/edit/open, payment-method setup, and notifications. App shell navigation lives in `src/layout/AppLayout.tsx`.

Local development:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Verification:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Pull requests that touch `frontend/**` run `frontend-ci` (typecheck and build).
