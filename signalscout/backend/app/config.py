from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SignalScout"
    environment: str = "development"
    ai_provider: str = "demo"
    ai_model: str = "deterministic-demo-v1"
    enrichment_provider: str = "demo"
    crm_provider: str = "demo"
    database_url: str = "sqlite:///./signalscout.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
