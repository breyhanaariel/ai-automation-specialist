from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any


class Store:
    def __init__(self, path: str = "signalscout.db") -> None:
        self.path = path
        self.lock = Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS leads(
              lead_id TEXT PRIMARY KEY, email TEXT NOT NULL, company TEXT NOT NULL,
              status TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
            CREATE TABLE IF NOT EXISTS audit_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL, event TEXT NOT NULL,
              detail TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """)

    def find_duplicate(self, email: str, company: str, exclude_id: str | None = None) -> bool:
        with self._connect() as c:
            row = c.execute(
                "SELECT lead_id FROM leads WHERE (lower(email)=lower(?) OR lower(company)=lower(?)) AND lead_id != COALESCE(?, '') LIMIT 1",
                (email, company, exclude_id),
            ).fetchone()
            return row is not None

    def save(self, lead_id: str, email: str, company: str, status: str, payload: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat()
        with self.lock, self._connect() as c:
            c.execute(
                """INSERT INTO leads(lead_id,email,company,status,payload,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(lead_id) DO UPDATE SET
                email=excluded.email, company=excluded.company, status=excluded.status,
                payload=excluded.payload, updated_at=excluded.updated_at""",
                (lead_id, email, company, status, json.dumps(payload), now, now),
            )
            c.execute("INSERT INTO audit_events(lead_id,event,detail,created_at) VALUES(?,?,?,?)",
                      (lead_id, "workflow_saved", status, now))

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM leads ORDER BY updated_at DESC").fetchall()]

    def metrics(self) -> dict[str, int]:
        with self._connect() as c:
            total = c.execute("SELECT count(*) FROM leads").fetchone()[0]
            rows = c.execute("SELECT status,count(*) n FROM leads GROUP BY status").fetchall()
        return {"total": total, **{r["status"]: r["n"] for r in rows}}
