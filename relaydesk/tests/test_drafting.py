from datetime import UTC, datetime

import pytest

from app.providers.base import LLMProvider, T
from app.schemas import (
    DraftResponse,
    Priority,
    RecommendedRoute,
    RetrievedSource,
    RiskFlag,
    Sentiment,
    SupportTicketIn,
    TicketCategory,
    TicketClassification,
)
from app.services.drafting import DraftingService


class UnknownCitationProvider(LLMProvider):
    name = "fake"
    model = "fake-model"

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        result = DraftResponse(
            draft_text="Please use the documented troubleshooting steps.",
            source_ids=["kb-does-not-exist"],
            requires_account_action=False,
            unsupported_action_claimed=False,
        )
        return response_model.model_validate(result.model_dump())


@pytest.mark.asyncio
async def test_draft_rejects_unknown_source_ids() -> None:
    ticket = SupportTicketIn(
        ticket_id="draft-001",
        customer_message="The app keeps crashing.",
        received_at=datetime.now(UTC),
    )
    classification = TicketClassification(
        category=TicketCategory.TECHNICAL_ISSUE,
        intent_summary="Customer reports an app crash.",
        priority=Priority.NORMAL,
        sentiment=Sentiment.NEUTRAL,
        confidence=0.94,
        risk_flags=[RiskFlag.NONE],
        recommended_route=RecommendedRoute.AUTO_ELIGIBLE,
        rationale_summary="Routine troubleshooting request.",
    )
    sources = [
        RetrievedSource(
            source_id="kb-technical",
            title="Technical troubleshooting",
            excerpt="Restart the app and collect error details if the issue persists.",
            relevance_score=0.8,
        )
    ]

    with pytest.raises(ValueError, match="unknown knowledge sources"):
        await DraftingService(UnknownCitationProvider()).draft(
            ticket,
            classification,
            sources,
        )
