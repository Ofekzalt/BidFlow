import asyncio
import signal

from auction.config import SessionLocal, settings
from auction.service.close_service import close_expired_batch


async def _close_one_batch() -> None:
    async with SessionLocal() as session:
        try:
            await close_expired_batch(session, settings.close_batch_size)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def run() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    while not stop.is_set():
        try:
            await _close_one_batch()
        except Exception:
            pass
        if stop.is_set():
            break
        try:
            await asyncio.wait_for(
                stop.wait(), timeout=settings.close_poll_interval_seconds
            )
        except TimeoutError:
            pass


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
