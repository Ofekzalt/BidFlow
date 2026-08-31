import asyncio
import signal

import aio_pika

from auction.config import settings
from auction.constants import QUEUE_PAYMENT_RESULT
from auction.messaging.consumer import handle_payment_result_message
from auction.messaging.topology import declare_topology


async def run() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    while not stop.is_set():
        connection = None
        try:
            connection = await aio_pika.connect(settings.rabbitmq_url, timeout=2)
            async with connection:
                channel = await connection.channel(on_return_raises=True)
                await channel.set_qos(prefetch_count=1)
                await declare_topology(channel, settings.rabbitmq_retry_delays)
                queue = await channel.get_queue(QUEUE_PAYMENT_RESULT)
                idle = asyncio.Event()
                idle.set()

                async def on_message(
                    message: aio_pika.abc.AbstractIncomingMessage,
                    bound_channel: aio_pika.abc.AbstractChannel = channel,
                    bound_idle: asyncio.Event = idle,
                ) -> None:
                    bound_idle.clear()
                    try:
                        await handle_payment_result_message(bound_channel, message)
                    finally:
                        bound_idle.set()

                consumer_tag = await queue.consume(on_message)
                await stop.wait()
                await queue.cancel(consumer_tag)
                await idle.wait()
        except Exception:
            if connection is not None and not connection.is_closed:
                await connection.close()
        if stop.is_set():
            break
        try:
            await asyncio.wait_for(stop.wait(), timeout=2)
        except TimeoutError:
            pass


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
