from __future__ import annotations

from datetime import UTC, datetime

from app.providers.base import LLMProvider, T
from app.schemas import (
    Priority,
    RecommendedRoute,
    RiskFlag,
    Sentiment,
    SupportTicketIn,
    TicketCategory,
    TicketClassification,
)
from app.services.classification import ClassificationService


class FakeProvider(LLMProvider):
    name = "fake"
    model = "fake-model"

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        assert "support-triage classifier" in system_prompt
        assert "ticket-001" in user_prompt
        result = TicketClassification(
            category=TicketCategory.BILLING,
            intent_summary="Customer asks about an unexpected charge.",
            priority=Priority.HIGH,
            sentiment=Sentiment.NEGATIVE,
            confidence=0.91,
            risk_flags=[RiskFlag.PAYMENT_DISPUTE],
            recommended_route=RecommendedRoute.HUMAN_REVIEW,
            rationale_summary="Billing dispute should be reviewed by a person.",
        )
        return response_model.model_validate(result.model_dump())


async def test_classification_service_returns_validated_model() -> None:
    ticket = SupportTicketIn(
        ticket_id="ticket-001",
        customer_message="I was charged twice and need help.",
        received_at=datetime.now(UTC),
    )
    result = await ClassificationService(FakeProvider()).classify(ticket)
    assert result.category == TicketCategory.BILLING
    assert result.confidence == 0.91
    assert RiskFlag.PAYMENT_DISPUTE in result.risk_flags
