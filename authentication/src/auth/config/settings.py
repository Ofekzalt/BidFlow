from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    jwt_secret: str
    jwt_issuer: str = "authentication"
    jwt_audience: str = "live-auction-platform"
    jwt_expires_seconds: int = 3600
    auth_port: int = 8001


settings = Settings()
