from datetime import UTC, datetime

from app.schemas import (
    Priority,
    RecommendedRoute,
    RiskFlag,
    Sentiment,
    SupportTicketIn,
    TicketCategory,
    TicketClassification,
)
from app.services.retrieval import KnowledgeRetriever


def test_account_access_ticket_retrieves_password_source_first() -> None:
    ticket = SupportTicketIn(
        ticket_id="retrieval-001",
        customer_message="I cannot log in and need to reset my password.",
        received_at=datetime.now(UTC),
    )
    classification = TicketClassification(
        category=TicketCategory.ACCOUNT_ACCESS,
        intent_summary="Customer needs password reset help.",
        priority=Priority.NORMAL,
        sentiment=Sentiment.NEUTRAL,
        confidence=0.95,
        risk_flags=[RiskFlag.NONE],
        recommended_route=RecommendedRoute.AUTO_ELIGIBLE,
        rationale_summary="Routine account access request.",
    )

    sources = KnowledgeRetriever().retrieve(ticket, classification)

    assert sources
    assert sources[0].source_id == "kb-password-reset"
    assert sources[0].relevance_score > 0
    assert len(sources) <= 3
