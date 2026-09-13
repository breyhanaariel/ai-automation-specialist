import json
from pathlib import Path

from evals.io import load_cases, load_predictions
from evals.scoring import meets_initial_targets, score


def write_predictions(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")


def test_benchmark_dataset_has_32_labeled_cases() -> None:
    cases = load_cases("data/support_tickets.jsonl")
    assert len(cases) == 32
    assert cases[0].ticket_id == "T001"
    assert cases[-1].ticket_id == "T032"


def test_scoring_calculates_accuracy_risk_and_safety(tmp_path) -> None:
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ticket_id": "A",
                        "expected_category": "billing",
                        "expected_priority": "high",
                        "expected_risk_flags": ["payment_dispute"],
                        "expected_route": "human_review",
                    }
                ),
                json.dumps(
                    {
                        "ticket_id": "B",
                        "expected_category": "product_question",
                        "expected_priority": "low",
                        "expected_risk_flags": ["none"],
                        "expected_route": "auto_eligible",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    predictions_path = tmp_path / "predictions.jsonl"
    write_predictions(
        predictions_path,
        [
            {
                "ticket_id": "A",
                "category": "billing",
                "priority": "high",
                "risk_flags": ["payment_dispute"],
                "route": "human_review",
                "schema_valid": True,
                "failed": False,
                "latency_ms": 120,
                "classification_latency_ms": 60,
                "retrieval_latency_ms": 10,
                "drafting_latency_ms": 50,
            },
            {
                "ticket_id": "B",
                "category": "product_question",
                "priority": "normal",
                "risk_flags": ["none"],
                "route": "auto_eligible",
                "schema_valid": True,
                "failed": False,
                "latency_ms": 80,
                "classification_latency_ms": 40,
                "retrieval_latency_ms": 10,
                "drafting_latency_ms": 30,
            },
        ],
    )

    report = score(load_cases(cases_path), load_predictions(predictions_path))

    assert report["metrics"]["category_accuracy_percent"] == 100.0
    assert report["metrics"]["priority_accuracy_percent"] == 50.0
    assert report["metrics"]["risk_recall_percent"] == 100.0
    assert report["metrics"]["routing_accuracy_percent"] == 100.0
    assert report["metrics"]["high_risk_auto_violations"] == 0
    assert report["latency_ms"]["end_to_end"]["mean"] == 100


def test_high_risk_auto_route_is_reported_as_safety_violation(tmp_path) -> None:
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(
        json.dumps(
            {
                "ticket_id": "A",
                "expected_category": "account_access",
                "expected_priority": "urgent",
                "expected_risk_flags": ["account_security"],
                "expected_route": "human_review",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    predictions_path = tmp_path / "predictions.jsonl"
    write_predictions(
        predictions_path,
        [
            {
                "ticket_id": "A",
                "category": "account_access",
                "priority": "urgent",
                "risk_flags": ["account_security"],
                "route": "auto_eligible",
                "schema_valid": True,
                "failed": False,
            }
        ],
    )

    report = score(load_cases(cases_path), load_predictions(predictions_path))
    targets = meets_initial_targets(report)

    assert report["metrics"]["high_risk_auto_violations"] == 1
    assert report["high_risk_auto_violation_ticket_ids"] == ["A"]
    assert targets["high_risk_safety"] is False
