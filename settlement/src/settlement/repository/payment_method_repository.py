import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from settlement.entity import PaymentMethod


async def list_by_user(
    session: AsyncSession, user_id: uuid.UUID
) -> list[PaymentMethod]:
    result = await session.execute(
        select(PaymentMethod)
        .where(PaymentMethod.user_id == user_id)
        .order_by(PaymentMethod.created_at)
    )
    return list(result.scalars().all())


async def get_default_by_user(
    session: AsyncSession, user_id: uuid.UUID
) -> PaymentMethod | None:
    result = await session.execute(
        select(PaymentMethod)
        .where(
            PaymentMethod.user_id == user_id,
            PaymentMethod.is_default.is_(True),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def clear_defaults_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(PaymentMethod)
        .where(PaymentMethod.user_id == user_id)
        .values(is_default=False)
    )


async def get_by_id(
    session: AsyncSession, method_id: uuid.UUID
) -> PaymentMethod | None:
    result = await session.execute(
        select(PaymentMethod).where(PaymentMethod.id == method_id)
    )
    return result.scalar_one_or_none()


async def get_by_stripe_payment_method_id(
    session: AsyncSession, stripe_payment_method_id: str
) -> PaymentMethod | None:
    result = await session.execute(
        select(PaymentMethod).where(
            PaymentMethod.stripe_payment_method_id == stripe_payment_method_id
        )
    )
    return result.scalar_one_or_none()


async def create_payment_method(
    session: AsyncSession,
    user_id: uuid.UUID,
    stripe_payment_method_id: str,
    *,
    is_default: bool,
) -> PaymentMethod:
    method = PaymentMethod(
        user_id=user_id,
        stripe_payment_method_id=stripe_payment_method_id,
        is_default=is_default,
    )
    session.add(method)
    await session.flush()
    return method


async def delete_payment_method(session: AsyncSession, method: PaymentMethod) -> None:
    await session.delete(method)
    await session.flush()
