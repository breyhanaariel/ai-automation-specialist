from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api import get_repository
from app.main import app
from app.persistence import WorkflowRepository
from app.schemas import SupportTicketIn, WorkflowState


def seed(repository: WorkflowRepository, workflow_id: str, status: str) -> WorkflowState:
    state = WorkflowState(
        workflow_id=workflow_id,
        ticket=SupportTicketIn(
            ticket_id=f"ticket-{workflow_id}",
            customer_message="Please review this request.",
            received_at=datetime.now(UTC),
            source="email",
        ),
        status=status,
    )
    repository.save_workflow(state)
    return state


def test_review_dashboard_is_served_from_fastapi() -> None:
    client = TestClient(app)

    root = client.get("/", follow_redirects=False)
    page = client.get("/review/")
    script = client.get("/review/app.js")
    styles = client.get("/review/styles.css")

    assert root.status_code in {302, 307}
    assert root.headers["location"] == "/review/"
    assert page.status_code == 200
    assert "Human Review Console" in page.text
    assert "Edit &amp; Approve" in page.text or "Edit & Approve" in page.text
    assert script.status_code == 200
    assert "/api/v1/workflows?status=awaiting_review" in script.text
    assert styles.status_code == 200


def test_review_queue_endpoint_filters_awaiting_workflows(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'dashboard.db'}")
    seed(repository, "review-1", "awaiting_review")
    seed(repository, "completed-1", "completed")
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.get("/api/v1/workflows?status=awaiting_review")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    workflows = response.json()
    assert len(workflows) == 1
    assert workflows[0]["workflow_id"] == "review-1"
    assert workflows[0]["status"] == "awaiting_review"


def test_repository_lists_most_recent_workflows_with_limit(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'list.db'}")
    seed(repository, "one", "awaiting_review")
    seed(repository, "two", "awaiting_review")

    workflows = repository.list_workflows(status="awaiting_review", limit=1)

    assert len(workflows) == 1
    assert workflows[0].workflow_id in {"one", "two"}
