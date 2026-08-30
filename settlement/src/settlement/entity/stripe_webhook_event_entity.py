from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from settlement.config import Base
from settlement.constants import STRIPE_WEBHOOK_EVENTS_TABLE_NAME


class StripeWebhookEvent(Base):
    __tablename__ = STRIPE_WEBHOOK_EVENTS_TABLE_NAME

    stripe_event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
