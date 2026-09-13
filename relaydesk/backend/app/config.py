from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RelayDesk"
    environment: str = "development"

    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5-coder:7b"
    llm_timeout_seconds: int = Field(default=60, ge=5, le=300)

    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    classification_auto_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    classification_review_threshold: float = Field(default=0.70, ge=0.0, le=1.0)

    database_url: str = "sqlite:///./relaydesk.db"


@lru_cache

def get_settings() -> Settings:
    return Settings()
