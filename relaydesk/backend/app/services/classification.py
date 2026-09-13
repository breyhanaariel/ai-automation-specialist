from __future__ import annotations

from app.prompts import CLASSIFICATION_SYSTEM_PROMPT, build_classification_prompt
from app.providers.base import LLMProvider
from app.schemas import SupportTicketIn, TicketClassification


class ClassificationService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def classify(self, ticket: SupportTicketIn) -> TicketClassification:
        return await self.provider.generate_structured(
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            user_prompt=build_classification_prompt(ticket),
            response_model=TicketClassification,
        )
