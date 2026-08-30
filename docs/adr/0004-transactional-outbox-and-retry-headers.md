# 0004 — Transactional outbox and retry headers

Status: Accepted
Date: 2026-08-30

## Context

Auction and settlement must exchange durable domain events without calling each other on the bid path. Writing to PostgreSQL and publishing to RabbitMQ in two independent steps can lose the event (commit succeeded, broker down) or publish an event that never committed.

Consumers retry poison messages. If retry count, original routing key, or last error live in the JSON body, retries mutate the domain event and break idempotency: the same `event_id` would no longer have a stable body.

Each service must own its messaging adapters. A shared library would couple deploy and version of auction and settlement.

## Decision

Each service writes domain state and an unpublished `outbox_events` row in the same PostgreSQL transaction. A publisher worker claims unpublished rows with `FOR UPDATE SKIP LOCKED`, publishes with persistent delivery and broker confirm, then sets `published_at`. If the broker is down, `published_at` stays null and a later run publishes the same row.

Domain event bodies are immutable envelopes: `event_id`, `event_type`, `event_version`, `occurred_at`, `correlation_id`, `producer`, `aggregate_id`, `payload`. Retry metadata lives only in RabbitMQ headers: `x-retry-count`, `x-original-routing-key`, `x-last-error`. Failed handlers ACK the original delivery after publishing to a delay queue or the dead-letter exchange so the body is unchanged.

Consumers ACK only after their database transaction commits. Duplicate deliveries are ignored via `processed_events(event_id)`. Auction and settlement each duplicate envelope, topology, publisher, consumer, and retry adapters; they do not import each other.

## Alternatives

- Dual-write to the database and the broker in the request or close path: simpler until the broker is down or the process dies between the two writes.
- Put retry fields in the payload: handlers can see failure context without headers, but the event is no longer a stable domain record.
- Shared `messaging` Python package: one implementation, but a cross-service import and a second release coupling.

## Consequences

- Committed winner closes survive RabbitMQ outages; consumers must tolerate at-least-once delivery.
- Payload builders reject retry header names so retry state cannot leak into the body.
- Topology includes per-queue TTL wait queues and a DLQ; delay values are settings so e2e can use sub-second delays.
- Settlement’s `AuctionEnded` consumer in this phase only records `processed_events`; Stripe charging remains Phase 6.
