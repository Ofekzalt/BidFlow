from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    settlement_port: int = 8003
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_api_base: str | None = None
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_retry_delays: str = "5,30,120"
    outbox_poll_interval_seconds: float = 2
    outbox_batch_size: int = 50


settings = Settings()
