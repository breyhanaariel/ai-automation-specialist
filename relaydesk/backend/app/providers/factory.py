from __future__ import annotations

from app.config import Settings
from app.providers.base import LLMProvider
from app.providers.demo import DemoProvider
from app.providers.ollama import OllamaProvider


def build_provider(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider.strip().lower()

    if provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if provider == "demo":
        return DemoProvider()

    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
        "Use 'ollama' for real local inference or 'demo' for the zero-cost public demo."
    )
