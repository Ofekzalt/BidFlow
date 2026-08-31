import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SetupIntentResponse(BaseModel):
    client_secret: str
    stripe_customer_id: str


class PaymentMethodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stripe_payment_method_id: str
    is_default: bool


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    payload: dict[str, Any]
    created_at: datetime
