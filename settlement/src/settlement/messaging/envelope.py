from typing import Any

from settlement.constants import (
    HEADER_LAST_ERROR,
    HEADER_ORIGINAL_ROUTING_KEY,
    HEADER_RETRY_COUNT,
)

RETRY_METADATA_KEYS = frozenset(
    {
        HEADER_RETRY_COUNT,
        HEADER_ORIGINAL_ROUTING_KEY,
        HEADER_LAST_ERROR,
    }
)


def build_envelope(
    *,
    event_id: str,
    event_type: str,
    event_version: str,
    occurred_at: str,
    correlation_id: str,
    producer: str,
    aggregate_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if RETRY_METADATA_KEYS & payload.keys():
        raise ValueError("retry metadata must not appear in the payload")
    return {
        "event_id": event_id,
        "event_type": event_type,
        "event_version": event_version,
        "occurred_at": occurred_at,
        "correlation_id": correlation_id,
        "producer": producer,
        "aggregate_id": aggregate_id,
        "payload": payload,
    }
