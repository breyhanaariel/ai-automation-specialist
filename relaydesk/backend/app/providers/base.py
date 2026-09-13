from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProviderError(RuntimeError):
    """Base exception for normalized provider failures."""


class ProviderUnavailableError(ProviderError):
    """Raised when the configured provider cannot be reached."""


class ProviderTimeoutError(ProviderError):
    """Raised when the provider exceeds the configured timeout."""


class ProviderOutputError(ProviderError):
    """Raised when provider output cannot be converted into the requested schema."""


class LLMProvider(ABC):
    """Vendor-neutral interface used by RelayDesk application services."""

    name: str
    model: str

    @abstractmethod
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        """Return provider output validated as the requested Pydantic model."""
        raise NotImplementedError
