# .github/

Repository-level automation and governance for Live Auction Platform.

## Owns

- Pull request templates
- CI workflows

## Does not own

- Application code
- Kong configuration
- Service runtime defaults
- Secrets

Workflows consume repository/environment secrets or federated credentials; sensitive values are never committed.

## Path-aware automation

When workflows are introduced, they should avoid unrelated work:

- `authentication/**` runs authentication e2e tests (service port until Kong exists, then through Kong) and affected gateway checks.
- `auction/**` runs auction e2e tests, concurrency scenarios, worker checks, and affected cross-module jobs.
- `settlement/**` runs settlement e2e tests, Stripe-fixture scenarios, messaging checks, and affected cross-module jobs.
- `frontend/**` runs TypeScript type checking and build; browser e2e when the UI exists.
- `gateway/**` runs gateway e2e checks.
- Shared contracts may intentionally run several jobs.

Path filtering is an optimization, not permission to skip cross-module verification when a contract changes.

CI should run e2e tests against owned PostgreSQL. Until Kong exists, hit the owning service port; after Phase 7, route API e2e through Kong. Do not add unit or integration test jobs.

## Delivery boundary

Automation validates repository changes. Deployment automation is not part of the current repository.

## Pull requests

Every pull request uses [`pull_request_template.md`](pull_request_template.md). The authoring agent identifies the owning modules, explains cross-module work, and provides verification evidence.

## Current state

The pull request template and module guidance provide baseline governance. Per-service CI workflows validate pull requests to `main`:

- `authentication-ci` — Ruff format and lint (e2e tests pending)
- `auction-ci` — Ruff, Alembic upgrade, e2e tests against Postgres and RabbitMQ
- `settlement-ci` — Ruff, e2e tests against Postgres and RabbitMQ

Workflows are path-filtered and documented in [`workflows/README.md`](workflows/README.md). Frontend jobs are not implemented yet. `gateway-ci` builds the Compose stack and runs Kong e2e tests.

Service-owned auction and settlement e2e still hit process ports with injected `X-User-Id`; they are not routed through Kong in this slice.
