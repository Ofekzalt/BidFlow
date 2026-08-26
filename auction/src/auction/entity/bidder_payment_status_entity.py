import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from auction.config import Base
from auction.constants import BIDDER_PAYMENT_STATUS_TABLE_NAME


class BidderPaymentStatus(Base):
    __tablename__ = BIDDER_PAYMENT_STATUS_TABLE_NAME

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    payment_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
