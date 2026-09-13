from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.models import BenchmarkCase, Prediction


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            ticket_id=str(record["ticket_id"]),
            expected_category=str(record["expected_category"]),
            expected_priority=str(record["expected_priority"]),
            expected_risk_flags=tuple(str(flag) for flag in record["expected_risk_flags"]),
            expected_route=str(record["expected_route"]),
        )
        for record in read_jsonl(path)
    ]


def load_predictions(path: str | Path) -> list[Prediction]:
    return [prediction_from_record(record) for record in read_jsonl(path)]


def prediction_from_record(record: dict[str, Any]) -> Prediction:
    return Prediction(
        ticket_id=str(record["ticket_id"]),
        category=_optional_str(record.get("category")),
        priority=_optional_str(record.get("priority")),
        risk_flags=tuple(str(flag) for flag in record.get("risk_flags", [])),
        route=_optional_str(record.get("route")),
        schema_valid=bool(record.get("schema_valid", False)),
        failed=bool(record.get("failed", False)),
        latency_ms=_optional_int(record.get("latency_ms")),
        classification_latency_ms=_optional_int(record.get("classification_latency_ms")),
        retrieval_latency_ms=_optional_int(record.get("retrieval_latency_ms")),
        drafting_latency_ms=_optional_int(record.get("drafting_latency_ms")),
        error=_optional_str(record.get("error")),
    )


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
    return records


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None
