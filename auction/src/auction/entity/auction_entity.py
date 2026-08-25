import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from auction.config import Base
from auction.constants import (
    AUCTION_STATUS_DRAFT,
    AUCTIONS_TABLE_NAME,
    TITLE_MAX_LENGTH,
)


class Auction(Base):
    __tablename__ = AUCTIONS_TABLE_NAME

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    starting_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    current_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    current_winner_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    final_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=AUCTION_STATUS_DRAFT
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
