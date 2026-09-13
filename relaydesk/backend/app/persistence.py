from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

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
                "CREATE INDEX IF NOT EXISTS idx_audit_workflow ON audit_events(workflow_id)"
            )

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
            rows = connection.execute(
                "SELECT event_json FROM audit_events WHERE event_type = 'workflow_completed'"
            ).fetchall()

        latencies = []
        for row in rows:
            payload = json.loads(row["event_json"])
            latency = payload.get("latency_ms")
            if isinstance(latency, int):
                latencies.append(latency)

        average_latency_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        automation_rate = round((completed / total) * 100, 2) if total else 0.0
        return {
            "total_workflows": total,
            "completed": completed,
            "awaiting_review": awaiting_review,
            "failed": failed,
            "automation_rate_percent": automation_rate,
            "average_completed_latency_ms": average_latency_ms,
        }
