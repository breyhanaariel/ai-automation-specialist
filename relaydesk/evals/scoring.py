from __future__ import annotations

from collections.abc import Iterable
from statistics import mean, median
from typing import Any

from evals.models import BenchmarkCase, Prediction


def score(cases: Iterable[BenchmarkCase], predictions: Iterable[Prediction]) -> dict[str, Any]:
    case_list = list(cases)
    prediction_map = {prediction.ticket_id: prediction for prediction in predictions}
    total = len(case_list)

    category_correct = 0
    priority_correct = 0
    route_correct = 0
    schema_successes = 0
    failures = 0
    auto_eligible = 0
    expected_risk_count = 0
    recovered_risk_count = 0
    high_risk_auto_violations: list[str] = []
    missing_predictions: list[str] = []
    per_ticket: list[dict[str, Any]] = []

    for case in case_list:
        prediction = prediction_map.get(case.ticket_id)
        if prediction is None:
            missing_predictions.append(case.ticket_id)
            per_ticket.append({"ticket_id": case.ticket_id, "missing_prediction": True})
            continue

        category_match = prediction.category == case.expected_category
        priority_match = prediction.priority == case.expected_priority
        route_match = prediction.route == case.expected_route
        category_correct += int(category_match)
        priority_correct += int(priority_match)
        route_correct += int(route_match)
        schema_successes += int(prediction.schema_valid)
        failures += int(prediction.failed)
        auto_eligible += int(prediction.route == "auto_eligible")

        expected_risks = {flag for flag in case.expected_risk_flags if flag != "none"}
        predicted_risks = {flag for flag in prediction.risk_flags if flag != "none"}
        expected_risk_count += len(expected_risks)
        recovered_risk_count += len(expected_risks & predicted_risks)
        if expected_risks and prediction.route == "auto_eligible":
            high_risk_auto_violations.append(case.ticket_id)

        per_ticket.append(
            {
                "ticket_id": case.ticket_id,
                "missing_prediction": False,
                "category_correct": category_match,
                "priority_correct": priority_match,
                "route_correct": route_match,
                "expected_risk_flags": sorted(expected_risks),
                "predicted_risk_flags": sorted(predicted_risks),
                "schema_valid": prediction.schema_valid,
                "failed": prediction.failed,
                "error": prediction.error,
            }
        )

    return {
        "label": "Benchmark result from a labeled synthetic dataset",
        "total_cases": total,
        "received_predictions": len(prediction_map),
        "missing_predictions": missing_predictions,
        "metrics": {
            "category_accuracy_percent": _percent(category_correct, total),
            "priority_accuracy_percent": _percent(priority_correct, total),
            "risk_recall_percent": _percent(recovered_risk_count, expected_risk_count),
            "routing_accuracy_percent": _percent(route_correct, total),
            "schema_success_rate_percent": _percent(schema_successes, total),
            "workflow_failure_rate_percent": _percent(failures, total),
            "automation_rate_percent": _percent(auto_eligible, total),
            "high_risk_auto_violations": len(high_risk_auto_violations),
        },
        "latency_ms": {
            "end_to_end": _latency_summary(
                [p.latency_ms for p in prediction_map.values() if p.latency_ms is not None]
            ),
            "classification": _latency_summary(
                [
                    p.classification_latency_ms
                    for p in prediction_map.values()
                    if p.classification_latency_ms is not None
                ]
            ),
            "retrieval": _latency_summary(
                [
                    p.retrieval_latency_ms
                    for p in prediction_map.values()
                    if p.retrieval_latency_ms is not None
                ]
            ),
            "drafting": _latency_summary(
                [
                    p.drafting_latency_ms
                    for p in prediction_map.values()
                    if p.drafting_latency_ms is not None
                ]
            ),
        },
        "high_risk_auto_violation_ticket_ids": high_risk_auto_violations,
        "per_ticket": per_ticket,
    }


def meets_initial_targets(report: dict[str, Any]) -> dict[str, bool]:
    metrics = report["metrics"]
    return {
        "category_accuracy": metrics["category_accuracy_percent"] >= 90.0,
        "routing_accuracy": metrics["routing_accuracy_percent"] >= 95.0,
        "risk_recall": metrics["risk_recall_percent"] >= 95.0,
        "schema_success": metrics["schema_success_rate_percent"] >= 98.0,
        "workflow_failure": metrics["workflow_failure_rate_percent"] < 2.0,
        "high_risk_safety": metrics["high_risk_auto_violations"] == 0,
    }


def _percent(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


def _latency_summary(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "p95": None}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered))))
    return {
        "count": len(values),
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "p95": ordered[p95_index],
    }
