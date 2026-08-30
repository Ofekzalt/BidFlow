import json
import uuid
from typing import Any

from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from auction.config import SessionLocal, settings
from auction.constants import (
    EVENT_TYPE_PAYMENT_METHOD_READY,
    EVENT_TYPE_PAYMENT_METHOD_REMOVED,
    QUEUE_PAYMENT_METHOD,
)
from auction.messaging.retry import retry_or_dead_letter
from auction.service import apply_payment_status


def parse_payment_method_event(
    body: dict[str, Any],
) -> tuple[uuid.UUID, uuid.UUID, bool, int]:
    event_type = body["event_type"]
    if event_type == EVENT_TYPE_PAYMENT_METHOD_READY:
        payment_ready = True
    elif event_type == EVENT_TYPE_PAYMENT_METHOD_REMOVED:
        payment_ready = False
    else:
        raise ValueError(f"unsupported event type {event_type}")
    payload = body["payload"]
    return (
        uuid.UUID(body["event_id"]),
        uuid.UUID(payload["user_id"]),
        payment_ready,
        int(payload["version"]),
    )


async def handle_payment_method_message(
    channel: AbstractChannel, message: AbstractIncomingMessage
) -> None:
    try:
        event_id, user_id, payment_ready, version = parse_payment_method_event(
            json.loads(message.body)
        )
        async with SessionLocal() as session:
            try:
                await apply_payment_status(
                    session, event_id, user_id, payment_ready, version
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        await message.ack()
    except Exception as exc:
        await retry_or_dead_letter(
            channel,
            message,
            queue_name=QUEUE_PAYMENT_METHOD,
            error=exc,
            retry_delays=settings.rabbitmq_retry_delays,
        )
