from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.providers.base import LLMProvider, ProviderUnavailableError, T
from app.schemas import (
    Priority,
    RecommendedRoute,
    RiskFlag,
    Sentiment,
    TicketCategory,
    TicketClassification,
)


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
        result = TicketClassification(
            category=TicketCategory.ACCOUNT_ACCESS,
            intent_summary="Customer reports suspicious account access.",
            priority=Priority.URGENT,
            sentiment=Sentiment.NEGATIVE,
            confidence=0.98,
            risk_flags=[RiskFlag.ACCOUNT_SECURITY],
            recommended_route=RecommendedRoute.AUTO_ELIGIBLE,
            rationale_summary="Possible account takeover requires human handling.",
        )
        return response_model.model_validate(result.model_dump())


class FailingProvider(LLMProvider):
    name = "fake"
    model = "fake-model"

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        raise ProviderUnavailableError("provider offline")


def payload() -> dict[str, object]:
    return {
        "ticket_id": "ticket-api-001",
        "customer_message": "Someone changed my password and I cannot log in.",
        "received_at": datetime.now(UTC).isoformat(),
        "source": "email",
    }


def test_classify_endpoint_returns_model_and_policy_decision(monkeypatch) -> None:
    monkeypatch.setattr("app.api.build_provider", lambda settings: FakeProvider())
    client = TestClient(app)

    response = client.post("/api/v1/classify", json=payload())

    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["confidence"] == 0.98
    assert body["classification"]["recommended_route"] == "auto_eligible"
    assert body["routing"]["route"] == "human_review"
    assert body["routing"]["policy_overrode_model"] is True
    assert body["provider"] == "fake"


def test_provider_failure_returns_normalized_503(monkeypatch) -> None:
    monkeypatch.setattr("app.api.build_provider", lambda settings: FailingProvider())
    client = TestClient(app)

    response = client.post("/api/v1/classify", json=payload())

    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["code"] == "ProviderUnavailableError"


def test_invalid_ticket_is_rejected_before_provider(monkeypatch) -> None:
    monkeypatch.setattr("app.api.build_provider", lambda settings: FakeProvider())
    client = TestClient(app)
    invalid = payload()
    invalid["customer_message"] = "   "

    response = client.post("/api/v1/classify", json=invalid)

    assert response.status_code == 422
