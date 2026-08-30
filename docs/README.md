# docs/

Architecture and operational knowledge for Live Auction Platform.

## Owns

- Approved product and architecture requirements
- Sequenced implementation work and verification
- [`adr/`](adr/) — architectural decisions and their trade-offs
- Future architecture diagrams, runbooks, and failure-demo documentation

## Does not own

- Application code
- Runtime configuration or secrets
- Kong, Compose, Helm, or CI definitions
- Claims that planned behavior is already implemented

## Documentation rules

- Distinguish approved intent, implemented behavior, and future options.
- Update documentation when ownership or public contracts change.
- Do not duplicate one decision across several documents without identifying the authoritative source.
- PRD changes alter requirements; ADRs explain significant choices; implementation plans describe execution.
- Use diagrams only when they make boundaries or flows clearer.

## Architecture decision records

Create an ADR when a meaningful architectural choice is made or changed. Include context, decision, alternatives, consequences, and status. Do not write ADRs merely to inflate the project.

## Current state

The PRD and implementation plan are approved planning artifacts. [`adr/0001-hs256-jwt-signing.md`](adr/0001-hs256-jwt-signing.md) records the JWT signing choice. [`adr/0002-kong-jwt-edge-identity.md`](adr/0002-kong-jwt-edge-identity.md) records Kong as the sole JWT verifier and trusted `X-User-Id` forwarding. [`adr/0003-auction-payment-eligibility-projection.md`](adr/0003-auction-payment-eligibility-projection.md) records Auction’s local payment-eligibility projection (`event_id` vs per-user `version`). [`adr/0004-transactional-outbox-and-retry-headers.md`](adr/0004-transactional-outbox-and-retry-headers.md) records transactional outbox publishing and retry metadata in RabbitMQ headers.
