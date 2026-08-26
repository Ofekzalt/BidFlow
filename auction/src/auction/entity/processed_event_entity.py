import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from auction.config import Base
from auction.constants import PROCESSED_EVENTS_TABLE_NAME


class ProcessedEvent(Base):
    __tablename__ = PROCESSED_EVENTS_TABLE_NAME

    event_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
