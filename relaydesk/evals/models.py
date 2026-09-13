from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkCase:
    ticket_id: str
    expected_category: str
    expected_priority: str
    expected_risk_flags: tuple[str, ...]
    expected_route: str


@dataclass(frozen=True)
class Prediction:
    ticket_id: str
    category: str | None
    priority: str | None
    risk_flags: tuple[str, ...]
    route: str | None
    schema_valid: bool
    failed: bool
    latency_ms: int | None = None
    classification_latency_ms: int | None = None
    retrieval_latency_ms: int | None = None
    drafting_latency_ms: int | None = None
    error: str | None = None
