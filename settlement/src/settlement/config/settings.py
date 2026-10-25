from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from settlement.constants.settlement_constants import (
    STRIPE_WEBHOOK_SECRET_PLACEHOLDER,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    settlement_port: int = 8003
    stripe_secret_key: str = Field(min_length=1)
    stripe_webhook_secret: str = Field(min_length=1)
    stripe_api_base: str | None = None
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_retry_delays: str = "5,30,120"
    outbox_poll_interval_seconds: float = 2
    outbox_batch_size: int = 50

    @field_validator("stripe_webhook_secret")
    @classmethod
    def webhook_secret_must_be_unique(cls, value: str) -> str:
        if value == STRIPE_WEBHOOK_SECRET_PLACEHOLDER:
            raise ValueError("STRIPE_WEBHOOK_SECRET must be a unique secret")
        return value


settings = Settings()
