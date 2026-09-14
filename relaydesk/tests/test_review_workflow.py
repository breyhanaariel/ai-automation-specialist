from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api import get_repository
from app.main import app
from app.persistence import WorkflowRepository
from app.schemas import (
    DraftResponse,
    RecommendedRoute,
    RoutingDecision,
    SupportTicketIn,
    WorkflowState,
)


def seed_awaiting_review(repository: WorkflowRepository) -> WorkflowState:
    ticket = SupportTicketIn(
        ticket_id="review-001",
        customer_message="Please help with my account.",
        received_at=datetime.now(UTC),
        source="email",
    )
    state = WorkflowState(
        workflow_id="workflow-review-001",
        ticket=ticket,
        draft=DraftResponse(
            draft_text="Here is the current draft.",
            source_ids=[],
        ),
        routing=RoutingDecision(
            route=RecommendedRoute.HUMAN_REVIEW,
            reason="Human judgment required.",
            model_recommendation=RecommendedRoute.HUMAN_REVIEW,
        ),
        status="awaiting_review",
    )
    repository.save_workflow(state)
    return state


def review_payload(action: str, edited_response: str | None = None) -> dict[str, object]:
    return {
        "ticket_id": "review-001",
        "action": action,
        "reviewer_id": "reviewer-demo",
        "reviewed_at": datetime.now(UTC).isoformat(),
        "edited_response": edited_response,
        "notes": "Reviewed in test.",
    }


def test_approve_moves_workflow_to_ready_for_action(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'review.db'}")
    seed_awaiting_review(repository)
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/workflows/workflow-review-001/review",
            json=review_payload("approve"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ready_for_action"
    saved = repository.get_workflow("workflow-review-001")
    assert saved is not None
    assert saved.status == "ready_for_action"
    events = repository.list_audit_events("workflow-review-001")
    assert events[-1].event_type == "human_review_decided"
    assert events[-1].details["action"] == "approve"


def test_edit_and_approve_persists_reviewer_edit(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'edit.db'}")
    seed_awaiting_review(repository)
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/workflows/workflow-review-001/review",
            json=review_payload("edit_and_approve", "Reviewer-approved edited response."),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    saved = repository.get_workflow("workflow-review-001")
    assert saved is not None
    assert saved.status == "ready_for_action"
    assert saved.draft is not None
    assert saved.draft.draft_text == "Reviewer-approved edited response."


def test_ready_workflow_completes_only_after_action_execution(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'complete.db'}")
    state = seed_awaiting_review(repository)
    state.status = "ready_for_action"
    repository.save_workflow(state)
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.post("/api/v1/workflows/workflow-review-001/complete")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    saved = repository.get_workflow("workflow-review-001")
    assert saved is not None
    assert saved.status == "completed"
    events = repository.list_audit_events("workflow-review-001")
    assert events[-1].event_type == "workflow_completed"


def test_reject_and_escalate_have_distinct_terminal_states(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'terminal.db'}")
    client = TestClient(app)
    app.dependency_overrides[get_repository] = lambda: repository

    try:
        seed_awaiting_review(repository)
        rejected = client.post(
            "/api/v1/workflows/workflow-review-001/review",
            json=review_payload("reject"),
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "rejected"

        state = seed_awaiting_review(repository)
        state.workflow_id = "workflow-review-002"
        repository.save_workflow(state)
        escalated = client.post(
            "/api/v1/workflows/workflow-review-002/review",
            json=review_payload("escalate"),
        )
        assert escalated.status_code == 200
        assert escalated.json()["status"] == "escalated"
    finally:
        app.dependency_overrides.clear()


def test_edit_and_approve_requires_edited_response(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'invalid.db'}")
    seed_awaiting_review(repository)
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/workflows/workflow-review-001/review",
            json=review_payload("edit_and_approve"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
