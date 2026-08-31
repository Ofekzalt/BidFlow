import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from settlement.config.stripe_client import create_stripe_client
from settlement.dto import SetupIntentResponse
from settlement.repository import create_customer, get_by_user_id


async def create_setup_intent(
    session: AsyncSession, user_id: uuid.UUID
) -> SetupIntentResponse:
    existing = await get_by_user_id(session, user_id)
    client = create_stripe_client()
    if existing is None:
        customer = await asyncio.to_thread(
            client.v1.customers.create,
            params={"metadata": {"user_id": str(user_id)}},
        )
        row = await create_customer(session, user_id, customer.id)
        stripe_customer_id = row.stripe_customer_id
    else:
        stripe_customer_id = existing.stripe_customer_id
    setup_intent = await asyncio.to_thread(
        client.v1.setup_intents.create,
        params={
            "customer": stripe_customer_id,
            "usage": "off_session",
            "automatic_payment_methods": {"enabled": True},
        },
    )
    assert setup_intent.client_secret is not None
    return SetupIntentResponse(
        client_secret=setup_intent.client_secret,
        stripe_customer_id=stripe_customer_id,
    )
