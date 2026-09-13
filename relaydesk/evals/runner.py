from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from evals.io import load_cases, load_predictions, read_jsonl, write_jsonl
from evals.scoring import meets_initial_targets, score

DEFAULT_DATASET = Path("data/support_tickets.jsonl")
DEFAULT_PREDICTIONS = Path("evals/results/predictions.jsonl")
DEFAULT_REPORT = Path("evals/results/report.json")


def run_live_benchmark(
    *,
    dataset_path: str | Path,
    base_url: str,
    timeout_seconds: float = 120.0,
) -> list[dict[str, Any]]:
    records = read_jsonl(dataset_path)
    predictions: list[dict[str, Any]] = []
    endpoint = f"{base_url.rstrip('/')}/api/v1/process"

    with httpx.Client(timeout=timeout_seconds) as client:
        for record in records:
            ticket_id = str(record["ticket_id"])
            payload = {
                "ticket_id": f"benchmark-{ticket_id}",
                "customer_message": record["customer_message"],
                "received_at": datetime.now(UTC).isoformat(),
                "source": "synthetic_benchmark",
            }
            try:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                body = response.json()
                classification = body["classification"]
                routing = body["routing"]
                stage_latency = body.get("stage_latency_ms", {})
                predictions.append(
                    {
                        "ticket_id": ticket_id,
                        "category": classification["category"],
                        "priority": classification["priority"],
                        "risk_flags": classification.get("risk_flags", []),
                        "route": routing["route"],
                        "schema_valid": True,
                        "failed": False,
                        "latency_ms": body.get("latency_ms"),
                        "classification_latency_ms": stage_latency.get("classification"),
                        "retrieval_latency_ms": stage_latency.get("retrieval"),
                        "drafting_latency_ms": stage_latency.get("drafting"),
                        "workflow_id": body.get("workflow_id"),
                        "provider": body.get("provider"),
                        "model": body.get("model"),
                    }
                )
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                predictions.append(
                    {
                        "ticket_id": ticket_id,
                        "category": None,
                        "priority": None,
                        "risk_flags": [],
                        "route": None,
                        "schema_valid": False,
                        "failed": True,
                        "error": str(exc),
                    }
                )

    return predictions


def build_report(dataset_path: str | Path, predictions_path: str | Path) -> dict[str, Any]:
    report = score(load_cases(dataset_path), load_predictions(predictions_path))
    report["initial_targets"] = meets_initial_targets(report)
    report["generated_at"] = datetime.now(UTC).isoformat()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or score the RelayDesk synthetic benchmark.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--predictions", default=str(DEFAULT_PREDICTIONS))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="Score an existing predictions JSONL file without calling RelayDesk.",
    )
    args = parser.parse_args()

    if not args.score_only:
        predictions = run_live_benchmark(dataset_path=args.dataset, base_url=args.base_url)
        write_jsonl(args.predictions, predictions)

    report = build_report(args.dataset, args.predictions)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({"metrics": report["metrics"], "initial_targets": report["initial_targets"]}, indent=2))


if __name__ == "__main__":
    main()
