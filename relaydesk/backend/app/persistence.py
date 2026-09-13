from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import AuditEvent, WorkflowState


class WorkflowRepository:
    def __init__(self, database_url: str) -> None:
        self.database_path = self._database_path(database_url)
        self._initialize()

    @staticmethod
    def _database_path(database_url: str) -> str:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("RelayDesk currently supports sqlite:/// database URLs only")
        path = database_url.removeprefix(prefix)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        return path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    ticket_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    event_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    ticket_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_workflow ON audit_events(workflow_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflows_status_updated "
                "ON workflows(status, updated_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflows_ticket ON workflows(ticket_id)"
            )

    def claim_ticket(self, ticket_id: str, workflow_id: str) -> str | None:
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO idempotency_keys(ticket_id, workflow_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (ticket_id, workflow_id, now),
                )
                return None
            except sqlite3.IntegrityError:
                row = connection.execute(
                    "SELECT workflow_id FROM idempotency_keys WHERE ticket_id = ?",
                    (ticket_id,),
                ).fetchone()
        return None if row is None else str(row["workflow_id"])

    def save_workflow(self, state: WorkflowState) -> None:
        now = datetime.now(UTC).isoformat()
        payload = state.model_dump_json()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO workflows (
                    workflow_id, ticket_id, status, state_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(workflow_id) DO UPDATE SET
                    status = excluded.status,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    state.workflow_id,
                    state.ticket.ticket_id,
                    state.status,
                    payload,
                    now,
                    now,
                ),
            )

    def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT state_json FROM workflows WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
        if row is None:
            return None
        return WorkflowState.model_validate_json(row["state_json"])

    def get_workflow_by_ticket(self, ticket_id: str) -> WorkflowState | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT state_json FROM workflows
                WHERE ticket_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (ticket_id,),
            ).fetchone()
        if row is None:
            return None
        return WorkflowState.model_validate_json(row["state_json"])

    def list_workflows(self, status: str | None = None, limit: int = 100) -> list[WorkflowState]:
        with self._connection() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT state_json FROM workflows ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT state_json FROM workflows
                    WHERE status = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
        return [WorkflowState.model_validate_json(row["state_json"]) for row in rows]

    def add_audit_event(self, event: AuditEvent) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    event_id, workflow_id, ticket_id, event_type, occurred_at, event_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.workflow_id,
                    event.ticket_id,
                    event.event_type,
                    event.occurred_at.isoformat(),
                    event.model_dump_json(),
                ),
            )

    def list_audit_events(self, workflow_id: str) -> list[AuditEvent]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT event_json FROM audit_events
                WHERE workflow_id = ?
                ORDER BY occurred_at ASC
                """,
                (workflow_id,),
            ).fetchall()
        return [AuditEvent.model_validate_json(row["event_json"]) for row in rows]

    def metrics(self) -> dict[str, int | float]:
        with self._connection() as connection:
            total = connection.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
            completed = connection.execute(
                "SELECT COUNT(*) FROM workflows WHERE status = 'completed'"
            ).fetchone()[0]
            awaiting_review = connection.execute(
                "SELECT COUNT(*) FROM workflows WHERE status = 'awaiting_review'"
            ).fetchone()[0]
            failed = connection.execute(
                "SELECT COUNT(*) FROM workflows WHERE status = 'failed'"
            ).fetchone()[0]
            replay_count = connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE event_type = 'idempotent_replay'"
            ).fetchone()[0]
            rows = connection.execute("SELECT state_json FROM workflows").fetchall()

        completed_latencies: list[int] = []
        classification_latencies: list[int] = []
        retrieval_latencies: list[int] = []
        drafting_latencies: list[int] = []
        retries = 0
        for row in rows:
            state = WorkflowState.model_validate_json(row["state_json"])
            retries += state.retry_count
            timings = state.stage_latencies_ms
            if state.status == "completed" and "total" in timings:
                completed_latencies.append(timings["total"])
            if "classification" in timings:
                classification_latencies.append(timings["classification"])
            if "retrieval" in timings:
                retrieval_latencies.append(timings["retrieval"])
            if "drafting" in timings:
                drafting_latencies.append(timings["drafting"])

        def average(values: list[int]) -> float:
            return round(sum(values) / len(values), 2) if values else 0.0

        automation_rate = round((completed / total) * 100, 2) if total else 0.0
        failure_rate = round((failed / total) * 100, 2) if total else 0.0
        return {
            "total_workflows": total,
            "completed": completed,
            "awaiting_review": awaiting_review,
            "failed": failed,
            "failure_rate_percent": failure_rate,
            "automation_rate_percent": automation_rate,
            "idempotent_replays": replay_count,
            "provider_retries": retries,
            "average_completed_latency_ms": average(completed_latencies),
            "average_classification_latency_ms": average(classification_latencies),
            "average_retrieval_latency_ms": average(retrieval_latencies),
            "average_drafting_latency_ms": average(drafting_latencies),
        }
