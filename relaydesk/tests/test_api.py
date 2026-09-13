from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import get_repository
from app.main import app
from app.persistence import WorkflowRepository
from app.providers.base import LLMProvider, ProviderUnavailableError, T
from app.schemas import (
    DraftResponse,
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

    def __init__(self) -> None:
        self.calls = 0

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        self.calls += 1
        if response_model is TicketClassification:
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

        result = DraftResponse(
            draft_text=(
                "Use the password reset link and do not share recovery codes. "
                "I am routing this for security review."
            ),
            source_ids=["kb-password-reset"],
            requires_account_action=True,
            unsupported_action_claimed=False,
        )
        return response_model.model_validate(result.model_dump())


class UnsafeDraftProvider(FakeProvider):
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        self.calls += 1
        if response_model is TicketClassification:
            safe = TicketClassification(
                category=TicketCategory.PRODUCT_QUESTION,
                intent_summary="Customer asks a routine product question.",
                priority=Priority.NORMAL,
                sentiment=Sentiment.NEUTRAL,
                confidence=0.98,
                risk_flags=[RiskFlag.NONE],
                recommended_route=RecommendedRoute.AUTO_ELIGIBLE,
                rationale_summary="Routine request.",
            )
            return response_model.model_validate(safe.model_dump())

        unsafe = DraftResponse(
            draft_text="Your account change has been completed.",
            source_ids=[],
            requires_account_action=True,
            unsupported_action_claimed=True,
        )
        return response_model.model_validate(unsafe.model_dump())


class FailingProvider(LLMProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.calls = 0

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        self.calls += 1
        raise ProviderUnavailableError("provider offline")


def payload(ticket_id: str | None = None) -> dict[str, object]:
    return {
        "ticket_id": ticket_id or f"ticket-{uuid4()}",
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


def test_process_endpoint_returns_grounded_draft_and_telemetry(monkeypatch) -> None:
    monkeypatch.setattr("app.api.build_provider", lambda settings: FakeProvider())
    client = TestClient(app)
    response = client.post(
        "/api/v1/process",
        json=payload(),
        headers={"X-Correlation-ID": "corr-test-001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sources"][0]["source_id"] == "kb-password-reset"
    assert body["draft"]["source_ids"] == ["kb-password-reset"]
    assert body["routing"]["route"] == "human_review"
    assert body["correlation_id"] == "corr-test-001"
    assert set(body["stage_latencies_ms"]) >= {"classification", "retrieval", "drafting", "total"}
    assert body["idempotent_replay"] is False


def test_duplicate_ticket_replays_without_new_provider_calls(monkeypatch, tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'idempotency.db'}")
    app.dependency_overrides[get_repository] = lambda: repository
    provider = FakeProvider()
    monkeypatch.setattr("app.api.build_provider", lambda settings: provider)
    client = TestClient(app)
    request = payload("ticket-idempotent-001")
    try:
        first = client.post("/api/v1/process", json=request)
        calls_after_first = provider.calls
        second = client.post("/api/v1/process", json=request)
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["workflow_id"] == first.json()["workflow_id"]
    assert second.json()["idempotent_replay"] is True
    assert provider.calls == calls_after_first
    events = repository.list_audit_events(first.json()["workflow_id"])
    assert events[-1].event_type == "idempotent_replay"


def test_unsafe_draft_forces_human_review(monkeypatch) -> None:
    monkeypatch.setattr("app.api.build_provider", lambda settings: UnsafeDraftProvider())
    client = TestClient(app)
    request = payload()
    request["customer_message"] = "What features are available?"
    response = client.post("/api/v1/process", json=request)
    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["unsupported_action_claimed"] is True
    assert body["routing"]["route"] == "human_review"
    assert body["routing"]["policy_overrode_model"] is True


def test_process_failure_is_persisted_with_retry_telemetry(monkeypatch, tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'failure.db'}")
    app.dependency_overrides[get_repository] = lambda: repository
    provider = FailingProvider()
    monkeypatch.setattr("app.api.build_provider", lambda settings: provider)
    client = TestClient(app)
    request = payload("ticket-failure-001")
    try:
        response = client.post("/api/v1/process", json=request)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    workflow_id = response.json()["detail"]["workflow_id"]
    state = repository.get_workflow(workflow_id)
    assert state is not None
    assert state.status == "failed"
    assert state.error_code == "ProviderUnavailableError"
    assert state.retry_count == 1
    assert provider.calls == 2
    events = repository.list_audit_events(workflow_id)
    assert any(event.event_type == "provider_retry" for event in events)


def test_provider_failure_returns_normalized_503(monkeypatch) -> None:
    monkeypatch.setattr("app.api.build_provider", lambda settings: FailingProvider())
    client = TestClient(app)
    response = client.post("/api/v1/classify", json=payload())
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ProviderUnavailableError"


def test_invalid_ticket_is_rejected_before_provider(monkeypatch) -> None:
    monkeypatch.setattr("app.api.build_provider", lambda settings: FakeProvider())
    client = TestClient(app)
    invalid = payload()
    invalid["customer_message"] = "   "
    response = client.post("/api/v1/classify", json=invalid)
    assert response.status_code == 422
