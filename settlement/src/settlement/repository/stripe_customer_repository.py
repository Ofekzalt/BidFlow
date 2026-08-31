import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from settlement.entity import StripeCustomer


async def get_by_user_id(
    session: AsyncSession, user_id: uuid.UUID
) -> StripeCustomer | None:
    result = await session.execute(
        select(StripeCustomer).where(StripeCustomer.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_by_stripe_customer_id(
    session: AsyncSession,
    stripe_customer_id: str,
    *,
    for_update: bool = False,
) -> StripeCustomer | None:
    stmt = select(StripeCustomer).where(
        StripeCustomer.stripe_customer_id == stripe_customer_id
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_customer(
    session: AsyncSession, user_id: uuid.UUID, stripe_customer_id: str
) -> StripeCustomer:
    customer = StripeCustomer(user_id=user_id, stripe_customer_id=stripe_customer_id)
    session.add(customer)
    await session.flush()
    return customer
