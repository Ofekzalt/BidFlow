import json
import uuid
from typing import Any

from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from settlement.config import settings
from settlement.constants import QUEUE_AUCTION_ENDED
from settlement.messaging.retry import retry_or_dead_letter
from settlement.service.charge_service import process_auction_ended


def parse_auction_ended_event(
    body: dict[str, Any],
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, int, str]:
    payload = body["payload"]
    return (
        uuid.UUID(body["event_id"]),
        uuid.UUID(payload["auction_id"]),
        uuid.UUID(payload["winner_id"]),
        int(payload["final_amount_cents"]),
        str(payload["currency"]),
    )


async def handle_auction_ended_message(
    channel: AbstractChannel, message: AbstractIncomingMessage
) -> None:
    try:
        event_id, auction_id, winner_id, amount_cents, currency = (
            parse_auction_ended_event(json.loads(message.body))
        )
        await process_auction_ended(
            event_id, auction_id, winner_id, amount_cents, currency
        )
        await message.ack()
    except Exception as exc:
        await retry_or_dead_letter(
            channel,
            message,
            queue_name=QUEUE_AUCTION_ENDED,
            error=exc,
            retry_delays=settings.rabbitmq_retry_delays,
        )
