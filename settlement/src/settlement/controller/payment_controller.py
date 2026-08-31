import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import SignatureVerificationError

from settlement.config import get_session
from settlement.constants import (
    NOTIFICATIONS_PATH,
    PAYMENTS_ROUTER_PREFIX,
    WEBHOOKS_STRIPE_PATH,
)
from settlement.dependencies import require_user_id
from settlement.dto import (
    NotificationResponse,
    PaymentMethodResponse,
    SetupIntentResponse,
)
from settlement.service import (
    create_setup_intent,
    handle_stripe_webhook,
    list_payment_methods,
    list_user_notifications,
    remove_payment_method,
)
from settlement.service.payment_result_service import PaymentIntentNotReadyError

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
UserId = Annotated[uuid.UUID, Depends(require_user_id)]


@router.post(f"{PAYMENTS_ROUTER_PREFIX}/setup-intent")
async def setup_intent(session: Session, user_id: UserId) -> SetupIntentResponse:
    return await create_setup_intent(session, user_id)


@router.get(f"{PAYMENTS_ROUTER_PREFIX}/methods")
async def payment_methods(
    session: Session, user_id: UserId
) -> list[PaymentMethodResponse]:
    return await list_payment_methods(session, user_id)


@router.delete(
    f"{PAYMENTS_ROUTER_PREFIX}/methods/{{method_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_method(
    method_id: uuid.UUID, session: Session, user_id: UserId
) -> None:
    await remove_payment_method(session, user_id, method_id)


@router.get(NOTIFICATIONS_PATH)
async def notifications(
    session: Session, user_id: UserId
) -> list[NotificationResponse]:
    return await list_user_notifications(session, user_id)


@router.post(WEBHOOKS_STRIPE_PATH)
async def stripe_webhook(
    request: Request,
    session: Session,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, bool]:
    payload = await request.body()
    try:
        await handle_stripe_webhook(session, payload, stripe_signature)
    except SignatureVerificationError:
        raise HTTPException(status_code=400) from None
    except PaymentIntentNotReadyError:
        raise HTTPException(status_code=503) from None
    return {"received": True}
