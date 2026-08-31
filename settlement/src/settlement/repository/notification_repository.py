import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from settlement.entity import Notification


async def insert_notification(
    session: AsyncSession,
    user_id: uuid.UUID,
    notification_type: str,
    payload: dict[str, Any],
) -> Notification:
    notification = Notification(
        user_id=user_id, type=notification_type, payload=payload
    )
    session.add(notification)
    await session.flush()
    return notification


async def list_by_user(session: AsyncSession, user_id: uuid.UUID) -> list[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())
