from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from auth.constants.auth_constants import JWT_SECRET_PLACEHOLDER


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    jwt_secret: str
    jwt_issuer: str = "authentication"
    jwt_audience: str = "live-auction-platform"
    jwt_expires_seconds: int = 3600
    auth_port: int = 8001

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_unique(cls, value: str) -> str:
        if not value.strip() or value == JWT_SECRET_PLACEHOLDER:
            raise ValueError("JWT_SECRET must be a unique secret")
        return value


settings = Settings()
