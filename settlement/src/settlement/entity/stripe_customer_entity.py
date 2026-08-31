import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from settlement.config import Base
from settlement.constants import STRIPE_CUSTOMERS_TABLE_NAME


class StripeCustomer(Base):
    __tablename__ = STRIPE_CUSTOMERS_TABLE_NAME

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    stripe_customer_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
