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

- `authentication/**` runs authentication tests and affected integration tests.
- `auction/**` runs auction, concurrency, worker, and affected integration tests.
- `settlement/**` runs settlement, Stripe-fixture, messaging, and affected integration tests.
- `frontend/**` runs TypeScript tests, type checking, and build.
- `gateway/**` runs gateway policy/integration checks.
- Shared contracts may intentionally run several jobs.

Path filtering is an optimization, not permission to skip cross-module verification when a contract changes.

## Delivery boundary

Automation validates repository changes. Deployment automation is not part of the current repository.

## Pull requests

Every pull request uses [`pull_request_template.md`](pull_request_template.md). The authoring agent identifies the owning modules, explains cross-module work, and provides verification evidence.

## Current state

The pull request template and module guidance provide baseline governance. Concrete CI workflows and ownership enforcement are not implemented yet.
