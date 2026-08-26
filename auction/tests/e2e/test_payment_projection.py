import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from auction.config.settings import settings
from auction.service import apply_payment_status, is_payment_ready

SessionFactory = async_sessionmaker[AsyncSession]


def _session_factory() -> tuple[SessionFactory, object]:
    engine = create_async_engine(
        settings.database_url, pool_pre_ping=True, poolclass=NullPool
    )
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _apply(
    sessions: SessionFactory,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    payment_ready: bool,
    version: int,
) -> None:
    async with sessions() as session:
        await apply_payment_status(session, event_id, user_id, payment_ready, version)
        await session.commit()


async def _ready(sessions: SessionFactory, user_id: uuid.UUID) -> bool:
    async with sessions() as session:
        return await is_payment_ready(session, user_id)


def test_payment_projection() -> None:
    async def scenario() -> None:
        sessions, engine = _session_factory()
        try:
            user_id = uuid.uuid4()
            assert await _ready(sessions, user_id) is False

            await _apply(sessions, uuid.uuid4(), user_id, True, 1)
            assert await _ready(sessions, user_id) is True

            await _apply(sessions, uuid.uuid4(), user_id, False, 2)
            assert await _ready(sessions, user_id) is False

            first_event = uuid.uuid4()
            await _apply(sessions, first_event, user_id, True, 5)
            assert await _ready(sessions, user_id) is True

            await _apply(sessions, first_event, user_id, False, 5)
            assert await _ready(sessions, user_id) is True

            stale_event = uuid.uuid4()
            await _apply(sessions, stale_event, user_id, False, 4)
            assert await _ready(sessions, user_id) is True

            newer_event = uuid.uuid4()
            await _apply(sessions, newer_event, user_id, False, 6)
            assert await _ready(sessions, user_id) is False

            same_version_event = uuid.uuid4()
            await _apply(sessions, same_version_event, user_id, True, 6)
            assert await _ready(sessions, user_id) is False
        finally:
            await engine.dispose()

    asyncio.run(scenario())
