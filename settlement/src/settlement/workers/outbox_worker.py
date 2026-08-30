import asyncio
import signal

import aio_pika

from settlement.config import SessionLocal, settings
from settlement.messaging import declare_topology, publish_outbox_event
from settlement.repository.outbox_repository import claim_unpublished, mark_published


async def _publish_one(channel: aio_pika.abc.AbstractChannel) -> bool:
    async with SessionLocal() as session:
        try:
            events = await claim_unpublished(session, 1)
            if not events:
                return False
            event = events[0]
            await publish_outbox_event(channel, event)
            await mark_published(event)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            raise


async def _publish_one_batch(channel: aio_pika.abc.AbstractChannel) -> None:
    for _ in range(settings.outbox_batch_size):
        if not await _publish_one(channel):
            return


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
                await declare_topology(channel, settings.rabbitmq_retry_delays)
                while not stop.is_set():
                    try:
                        await _publish_one_batch(channel)
                    except Exception:
                        break
                    if stop.is_set():
                        break
                    try:
                        await asyncio.wait_for(
                            stop.wait(),
                            timeout=settings.outbox_poll_interval_seconds,
                        )
                    except TimeoutError:
                        pass
        except Exception:
            if connection is not None and not connection.is_closed:
                await connection.close()
        if stop.is_set():
            break
        try:
            await asyncio.wait_for(
                stop.wait(), timeout=settings.outbox_poll_interval_seconds
            )
        except TimeoutError:
            pass


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
