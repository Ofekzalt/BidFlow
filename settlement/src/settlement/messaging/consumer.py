import json
import uuid
from typing import Any

from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from settlement.config import SessionLocal, settings
from settlement.constants import QUEUE_AUCTION_ENDED
from settlement.messaging.retry import retry_or_dead_letter
from settlement.repository import record_event_id


def parse_auction_ended_event(body: dict[str, Any]) -> uuid.UUID:
    return uuid.UUID(body["event_id"])


async def handle_auction_ended_message(
    channel: AbstractChannel, message: AbstractIncomingMessage
) -> None:
    try:
        event_id = parse_auction_ended_event(json.loads(message.body))
        async with SessionLocal() as session:
            try:
                await record_event_id(session, event_id)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        await message.ack()
    except Exception as exc:
        await retry_or_dead_letter(
            channel,
            message,
            queue_name=QUEUE_AUCTION_ENDED,
            error=exc,
            retry_delays=settings.rabbitmq_retry_delays,
        )
