import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auction.constants import (
    ERROR_START_BEFORE_END,
    ERROR_STARTING_PRICE_POSITIVE,
    TITLE_MAX_LENGTH,
)


class CreateAuctionRequest(BaseModel):
    title: str = Field(max_length=TITLE_MAX_LENGTH)
    description: str
    starting_price_cents: int
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_price_and_times(self) -> "CreateAuctionRequest":
        if self.starting_price_cents <= 0:
            raise ValueError(ERROR_STARTING_PRICE_POSITIVE)
        if self.start_time >= self.end_time:
            raise ValueError(ERROR_START_BEFORE_END)
        return self


class PatchAuctionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=TITLE_MAX_LENGTH)
    description: str | None = None
    starting_price_cents: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_price(self) -> "PatchAuctionRequest":
        if self.starting_price_cents is not None and self.starting_price_cents <= 0:
            raise ValueError(ERROR_STARTING_PRICE_POSITIVE)
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            raise ValueError(ERROR_START_BEFORE_END)
        return self


class AuctionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    title: str
    description: str
    starting_price_cents: int
    current_price_cents: int
    current_winner_id: uuid.UUID | None
    final_amount_cents: int | None
    winner_id: uuid.UUID | None
    status: str
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: datetime


class CurrentBidResponse(BaseModel):
    amount_cents: int
    bidder_id: uuid.UUID | None
