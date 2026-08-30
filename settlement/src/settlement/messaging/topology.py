from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel

from settlement.constants import (
    EVENT_TYPE_PAYMENT_FAILED,
    EVENT_TYPE_PAYMENT_METHOD_READY,
    EVENT_TYPE_PAYMENT_METHOD_REMOVED,
    EVENT_TYPE_PAYMENT_SUCCEEDED,
    EVENT_VERSION_V1,
    QUEUE_AUCTION_ENDED,
    QUEUE_DLQ,
    QUEUE_PAYMENT_METHOD,
    QUEUE_PAYMENT_RESULT,
    RABBITMQ_DLX_EXCHANGE,
    RABBITMQ_EVENTS_EXCHANGE,
    RABBITMQ_RETRY_EXCHANGE,
    ROUTING_KEY_AUCTION_ENDED,
    ROUTING_KEY_PAYMENT_FAILED,
    ROUTING_KEY_PAYMENT_METHOD_READY,
    ROUTING_KEY_PAYMENT_METHOD_REMOVED,
    ROUTING_KEY_PAYMENT_SUCCEEDED,
)

EVENT_ROUTING_KEYS = {
    (EVENT_TYPE_PAYMENT_METHOD_READY, EVENT_VERSION_V1): (
        ROUTING_KEY_PAYMENT_METHOD_READY
    ),
    (EVENT_TYPE_PAYMENT_METHOD_REMOVED, EVENT_VERSION_V1): (
        ROUTING_KEY_PAYMENT_METHOD_REMOVED
    ),
    (EVENT_TYPE_PAYMENT_SUCCEEDED, EVENT_VERSION_V1): ROUTING_KEY_PAYMENT_SUCCEEDED,
    (EVENT_TYPE_PAYMENT_FAILED, EVENT_VERSION_V1): ROUTING_KEY_PAYMENT_FAILED,
}


def routing_key_for(event_type: str, event_version: str) -> str:
    key = EVENT_ROUTING_KEYS.get((event_type, event_version))
    if key is None:
        raise ValueError(f"unknown event {event_type}.{event_version}")
    return key


def retry_delay_seconds(raw: str) -> list[float]:
    return [float(part) for part in raw.split(",") if part.strip()]


def retry_routing_key(queue_name: str, delay_ms: int) -> str:
    return f"{queue_name}.{delay_ms}"


async def declare_topology(channel: AbstractChannel, retry_delays: str) -> None:
    events = await channel.declare_exchange(
        RABBITMQ_EVENTS_EXCHANGE, ExchangeType.TOPIC, durable=True
    )
    retry_exchange = await channel.declare_exchange(
        RABBITMQ_RETRY_EXCHANGE, ExchangeType.DIRECT, durable=True
    )
    dlx = await channel.declare_exchange(
        RABBITMQ_DLX_EXCHANGE, ExchangeType.FANOUT, durable=True
    )

    auction_ended = await channel.declare_queue(QUEUE_AUCTION_ENDED, durable=True)
    await auction_ended.bind(events, ROUTING_KEY_AUCTION_ENDED)

    payment_method = await channel.declare_queue(QUEUE_PAYMENT_METHOD, durable=True)
    await payment_method.bind(events, ROUTING_KEY_PAYMENT_METHOD_READY)
    await payment_method.bind(events, ROUTING_KEY_PAYMENT_METHOD_REMOVED)

    payment_result = await channel.declare_queue(QUEUE_PAYMENT_RESULT, durable=True)
    await payment_result.bind(events, ROUTING_KEY_PAYMENT_SUCCEEDED)
    await payment_result.bind(events, ROUTING_KEY_PAYMENT_FAILED)

    dlq = await channel.declare_queue(QUEUE_DLQ, durable=True)
    await dlq.bind(dlx)

    for queue_name in (
        QUEUE_AUCTION_ENDED,
        QUEUE_PAYMENT_METHOD,
        QUEUE_PAYMENT_RESULT,
    ):
        for delay in retry_delay_seconds(retry_delays):
            delay_ms = int(delay * 1000)
            wait_queue = await channel.declare_queue(
                f"{queue_name}.retry.{delay_ms}ms",
                durable=True,
                arguments={
                    "x-message-ttl": delay_ms,
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": queue_name,
                },
            )
            await wait_queue.bind(
                retry_exchange, routing_key=retry_routing_key(queue_name, delay_ms)
            )
