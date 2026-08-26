import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from auction.config import Base
from auction.constants import BIDS_TABLE_NAME


class Bid(Base):
    __tablename__ = BIDS_TABLE_NAME

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    auction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auctions.id"), nullable=False
    )
    bidder_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
