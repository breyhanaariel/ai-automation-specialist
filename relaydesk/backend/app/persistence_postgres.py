from __future__ import annotations

from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row

from app.schemas import AuditEvent, WorkflowState


class PostgresWorkflowRepository:
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise ValueError("Postgres repository requires a postgres database URL")
        self.database_url = database_url
        self._initialize()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _initialize(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                status TEXT NOT NULL,
                state_json JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                ticket_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                event_json JSONB NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                ticket_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_audit_workflow ON audit_events(workflow_id)",
            """
            CREATE INDEX IF NOT EXISTS idx_workflows_status_updated
            ON workflows(status, updated_at DESC)
            """,
            "CREATE INDEX IF NOT EXISTS idx_workflows_ticket ON workflows(ticket_id)",
        ]
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)

    def claim_ticket(self, ticket_id: str, workflow_id: str) -> str | None:
        now = datetime.now(UTC)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO idempotency_keys(ticket_id, workflow_id, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(ticket_id) DO NOTHING
                    RETURNING workflow_id
                    """,
                    (ticket_id, workflow_id, now),
                )
                inserted = cursor.fetchone()
                if inserted is not None:
                    return None
                cursor.execute(
                    "SELECT workflow_id FROM idempotency_keys WHERE ticket_id = %s",
                    (ticket_id,),
                )
                row = cursor.fetchone()
        return None if row is None else str(row["workflow_id"])

    def save_workflow(self, state: WorkflowState) -> None:
        now = datetime.now(UTC)
        payload = state.model_dump_json()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflows (
                        workflow_id, ticket_id, status, state_json, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s::jsonb, %s, %s)
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
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT state_json::text AS state_json FROM workflows WHERE workflow_id = %s",
                    (workflow_id,),
                )
                row = cursor.fetchone()
        return None if row is None else WorkflowState.model_validate_json(row["state_json"])

    def get_workflow_by_ticket(self, ticket_id: str) -> WorkflowState | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT state_json::text AS state_json FROM workflows
                    WHERE ticket_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (ticket_id,),
                )
                row = cursor.fetchone()
        return None if row is None else WorkflowState.model_validate_json(row["state_json"])

    def list_workflows(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[WorkflowState]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if status is None:
                    cursor.execute(
                        """
                        SELECT state_json::text AS state_json FROM workflows
                        ORDER BY updated_at DESC LIMIT %s
                        """,
                        (limit,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT state_json::text AS state_json FROM workflows
                        WHERE status = %s
                        ORDER BY updated_at DESC LIMIT %s
                        """,
                        (status, limit),
                    )
                rows = cursor.fetchall()
        return [WorkflowState.model_validate_json(row["state_json"]) for row in rows]

    def add_audit_event(self, event: AuditEvent) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, workflow_id, ticket_id, event_type, occurred_at, event_json
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT(event_id) DO NOTHING
                    """,
                    (
                        event.event_id,
                        event.workflow_id,
                        event.ticket_id,
                        event.event_type,
                        event.occurred_at,
                        event.model_dump_json(),
                    ),
                )

    def list_audit_events(self, workflow_id: str) -> list[AuditEvent]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT event_json::text AS event_json FROM audit_events
                    WHERE workflow_id = %s
                    ORDER BY occurred_at ASC
                    """,
                    (workflow_id,),
                )
                rows = cursor.fetchall()
        return [AuditEvent.model_validate_json(row["event_json"]) for row in rows]

    def metrics(self) -> dict[str, int | float]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT status, state_json::text AS state_json FROM workflows")
                rows = cursor.fetchall()
                cursor.execute(
                    "SELECT COUNT(*) AS count FROM audit_events "
                    "WHERE event_type = 'idempotent_replay'"
                )
                replay_count = int(cursor.fetchone()["count"])

        total = len(rows)
        completed = sum(1 for row in rows if row["status"] == "completed")
        ready_for_action = sum(1 for row in rows if row["status"] == "ready_for_action")
        awaiting_review = sum(1 for row in rows if row["status"] == "awaiting_review")
        rejected = sum(1 for row in rows if row["status"] == "rejected")
        escalated = sum(1 for row in rows if row["status"] == "escalated")
        failed = sum(1 for row in rows if row["status"] == "failed")
        retries = 0
        processing_latencies: list[int] = []
        classification_latencies: list[int] = []
        retrieval_latencies: list[int] = []
        drafting_latencies: list[int] = []

        for row in rows:
            state = WorkflowState.model_validate_json(row["state_json"])
            retries += state.retry_count
            timings = state.stage_latencies_ms
            if "total" in timings:
                processing_latencies.append(timings["total"])
            if "classification" in timings:
                classification_latencies.append(timings["classification"])
            if "retrieval" in timings:
                retrieval_latencies.append(timings["retrieval"])
            if "drafting" in timings:
                drafting_latencies.append(timings["drafting"])

        def average(values: list[int]) -> float:
            return round(sum(values) / len(values), 2) if values else 0.0

        ready_rate = round((ready_for_action / total) * 100, 2) if total else 0.0
        failure_rate = round((failed / total) * 100, 2) if total else 0.0
        return {
            "total_workflows": total,
            "ready_for_action": ready_for_action,
            "completed": completed,
            "awaiting_review": awaiting_review,
            "rejected": rejected,
            "escalated": escalated,
            "failed": failed,
            "failure_rate_percent": failure_rate,
            "auto_ready_rate_percent": ready_rate,
            "idempotent_replays": replay_count,
            "provider_retries": retries,
            "average_processing_latency_ms": average(processing_latencies),
            "average_classification_latency_ms": average(classification_latencies),
            "average_retrieval_latency_ms": average(retrieval_latencies),
            "average_drafting_latency_ms": average(drafting_latencies),
        }
