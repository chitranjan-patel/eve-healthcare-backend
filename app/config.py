from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://eve:eve@localhost:5432/eve_healthcare"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    webhook_secret: str = "dev-webhook-secret"
    cache_ttl_seconds: int = 60
    payment_success_rate: float = 0.8
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
