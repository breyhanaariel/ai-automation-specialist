from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from app.providers.base import (
    LLMProvider,
    ProviderOutputError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    T,
)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, *, base_url: str, model: str, timeout_seconds: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        payload = {
            "model": self.model,
            "stream": False,
            "format": response_model.model_json_schema(),
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Ollama exceeded the {self.timeout_seconds}s timeout"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"Ollama request failed: {exc}") from exc

        try:
            body = response.json()
            content = body["message"]["content"]
            raw = json.loads(content) if isinstance(content, str) else content
            return response_model.model_validate(raw)
        except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise ProviderOutputError(
                f"Ollama returned output that did not match {response_model.__name__}"
            ) from exc
