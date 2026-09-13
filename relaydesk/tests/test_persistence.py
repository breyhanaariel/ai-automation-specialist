from __future__ import annotations

from datetime import UTC, datetime

from app.persistence import WorkflowRepository
from app.schemas import AuditEvent, SupportTicketIn, WorkflowState


def ticket(ticket_id: str = "persist-001") -> SupportTicketIn:
    return SupportTicketIn(
        ticket_id=ticket_id,
        customer_message="How do I reset my password?",
        received_at=datetime.now(UTC),
    )


def test_workflow_state_round_trips(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'relaydesk.db'}")
    state = WorkflowState(
        workflow_id="workflow-001",
        ticket=ticket(),
        correlation_id="corr-001",
        stage_latencies_ms={"classification": 10},
    )
    repository.save_workflow(state)
    state.status = "classified"
    repository.save_workflow(state)
    restored = repository.get_workflow("workflow-001")
    assert restored is not None
    assert restored.ticket.ticket_id == "persist-001"
    assert restored.status == "classified"
    assert restored.correlation_id == "corr-001"
    assert restored.stage_latencies_ms["classification"] == 10


def test_ticket_claim_is_idempotent(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'claim.db'}")
    assert repository.claim_ticket("ticket-1", "workflow-1") is None
    assert repository.claim_ticket("ticket-1", "workflow-2") == "workflow-1"


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


def test_metrics_report_reliability_and_stage_latency(tmp_path) -> None:
    repository = WorkflowRepository(f"sqlite:///{tmp_path / 'relaydesk.db'}")
    states = [
        WorkflowState(
            workflow_id="workflow-1",
            ticket=ticket("persist-1"),
            status="completed",
            stage_latencies_ms={"classification": 40, "retrieval": 10, "drafting": 60, "total": 120},
            retry_count=1,
        ),
        WorkflowState(
            workflow_id="workflow-2",
            ticket=ticket("persist-2"),
            status="awaiting_review",
            stage_latencies_ms={"classification": 20, "retrieval": 6, "drafting": 30, "total": 70},
        ),
        WorkflowState(
            workflow_id="workflow-3",
            ticket=ticket("persist-3"),
            status="failed",
            stage_latencies_ms={"classification": 25, "total": 50},
        ),
    ]
    for state in states:
        repository.save_workflow(state)

    repository.add_audit_event(
        AuditEvent(
            event_id="event-replay",
            ticket_id="persist-1",
            event_type="idempotent_replay",
            occurred_at=datetime.now(UTC),
            workflow_id="workflow-1",
        )
    )
    metrics = repository.metrics()
    assert metrics["total_workflows"] == 3
    assert metrics["completed"] == 1
    assert metrics["awaiting_review"] == 1
    assert metrics["failed"] == 1
    assert metrics["failure_rate_percent"] == 33.33
    assert metrics["automation_rate_percent"] == 33.33
    assert metrics["idempotent_replays"] == 1
    assert metrics["provider_retries"] == 1
    assert metrics["average_completed_latency_ms"] == 120.0
    assert metrics["average_classification_latency_ms"] == 28.33
    assert metrics["average_retrieval_latency_ms"] == 8.0
    assert metrics["average_drafting_latency_ms"] == 45.0
