from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from settlement.constants import (
    HEADER_LAST_ERROR,
    HEADER_ORIGINAL_ROUTING_KEY,
    HEADER_RETRY_COUNT,
    RABBITMQ_DLX_EXCHANGE,
    RABBITMQ_RETRY_EXCHANGE,
)
from settlement.messaging.topology import retry_delay_seconds, retry_routing_key


async def retry_or_dead_letter(
    channel: AbstractChannel,
    message: AbstractIncomingMessage,
    *,
    queue_name: str,
    error: Exception,
    retry_delays: str,
) -> None:
    headers = dict(message.headers) if message.headers else {}
    count = int(headers.get(HEADER_RETRY_COUNT, 0))
    original = str(headers.get(HEADER_ORIGINAL_ROUTING_KEY) or message.routing_key)
    headers[HEADER_ORIGINAL_ROUTING_KEY] = original
    headers[HEADER_LAST_ERROR] = str(error)[:512]
    delays = retry_delay_seconds(retry_delays)
    if count >= len(delays):
        outgoing = Message(
            body=message.body,
            content_type=message.content_type,
            delivery_mode=DeliveryMode.PERSISTENT,
            headers=headers,
            message_id=message.message_id,
        )
        dlx = await channel.get_exchange(RABBITMQ_DLX_EXCHANGE)
        await dlx.publish(outgoing, routing_key=original)
    else:
        headers[HEADER_RETRY_COUNT] = count + 1
        outgoing = Message(
            body=message.body,
            content_type=message.content_type,
            delivery_mode=DeliveryMode.PERSISTENT,
            headers=headers,
            message_id=message.message_id,
        )
        delay_ms = int(delays[count] * 1000)
        retry_exchange = await channel.get_exchange(RABBITMQ_RETRY_EXCHANGE)
        await retry_exchange.publish(
            outgoing, routing_key=retry_routing_key(queue_name, delay_ms)
        )
    await message.ack()
