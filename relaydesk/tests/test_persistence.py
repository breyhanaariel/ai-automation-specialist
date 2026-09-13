from __future__ import annotations

from datetime import UTC, datetime

from app.persistence import WorkflowRepository
from app.schemas import AuditEvent, SupportTicketIn, WorkflowState


def ticket() -> SupportTicketIn:
    return SupportTicketIn(
        ticket_id="persist-001",
        customer_message="How do I reset my password?",
        received_at=datetime.now(UTC),
    )


def test_workflow_state_round_trips(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'relaydesk.db'}")
    state = WorkflowState(workflow_id="workflow-001", ticket=ticket())
    repository.save_workflow(state)

    state.status = "classified"
    repository.save_workflow(state)

    restored = repository.get_workflow("workflow-001")

    assert restored is not None
    assert restored.ticket.ticket_id == "persist-001"
    assert restored.status == "classified"


def test_audit_events_are_returned_in_time_order(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'relaydesk.db'}")
    repository.save_workflow(WorkflowState(workflow_id="workflow-001", ticket=ticket()))

    first = AuditEvent(
        event_id="event-1",
        ticket_id="persist-001",
        event_type="workflow_received",
        occurred_at=datetime(2026, 9, 13, 3, 0, tzinfo=UTC),
        workflow_id="workflow-001",
    )
    second = AuditEvent(
        event_id="event-2",
        ticket_id="persist-001",
        event_type="ticket_classified",
        occurred_at=datetime(2026, 9, 13, 3, 1, tzinfo=UTC),
        workflow_id="workflow-001",
    )
    repository.add_audit_event(second)
    repository.add_audit_event(first)

    events = repository.list_audit_events("workflow-001")

    assert [event.event_id for event in events] == ["event-1", "event-2"]


def test_metrics_report_completion_review_failure_and_latency(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'relaydesk.db'}")
    statuses = ["completed", "awaiting_review", "failed"]
    for index, workflow_status in enumerate(statuses, start=1):
        state = WorkflowState(workflow_id=f"workflow-{index}", ticket=ticket())
        state.status = workflow_status
        repository.save_workflow(state)

    repository.add_audit_event(
        AuditEvent(
            event_id="event-complete",
            ticket_id="persist-001",
            event_type="workflow_completed",
            occurred_at=datetime.now(UTC),
            workflow_id="workflow-1",
            latency_ms=120,
        )
    )

    metrics = repository.metrics()

    assert metrics["total_workflows"] == 3
    assert metrics["completed"] == 1
    assert metrics["awaiting_review"] == 1
    assert metrics["failed"] == 1
    assert metrics["automation_rate_percent"] == 33.33
    assert metrics["average_completed_latency_ms"] == 120.0
