import json
import uuid

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel

from settlement.constants import PRODUCER_SETTLEMENT, RABBITMQ_EVENTS_EXCHANGE
from settlement.entity.outbox_event_entity import OutboxEvent
from settlement.messaging.envelope import build_envelope
from settlement.messaging.topology import routing_key_for


async def publish_outbox_event(
    channel: AbstractChannel, event: OutboxEvent
) -> None:
    occurred_at = event.created_at.isoformat()
    envelope = build_envelope(
        event_id=str(event.id),
        event_type=event.event_type,
        event_version=event.event_version,
        occurred_at=occurred_at,
        correlation_id=str(uuid.uuid4()),
        producer=PRODUCER_SETTLEMENT,
        aggregate_id=str(event.aggregate_id),
        payload=event.payload,
    )
    routing_key = routing_key_for(event.event_type, event.event_version)
    exchange = await channel.get_exchange(RABBITMQ_EVENTS_EXCHANGE)
    message = Message(
        body=json.dumps(envelope).encode(),
        content_type="application/json",
        delivery_mode=DeliveryMode.PERSISTENT,
        message_id=str(event.id),
    )
    await exchange.publish(message, routing_key=routing_key, mandatory=True)
