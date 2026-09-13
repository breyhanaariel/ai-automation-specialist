import json
from pathlib import Path


def load_workflow(filename: str) -> dict[str, object]:
    path = Path("n8n") / filename
    return json.loads(path.read_text(encoding="utf-8"))


def node_types(workflow: dict[str, object]) -> set[str]:
    nodes = workflow["nodes"]
    assert isinstance(nodes, list)
    return {node["type"] for node in nodes if isinstance(node, dict)}


def test_intake_workflow_is_importable_json_with_required_nodes() -> None:
    workflow = load_workflow("relaydesk-intake.json")

    assert workflow["name"] == "RelayDesk - Support Intake"
    assert workflow["active"] is False
    types = node_types(workflow)
    assert "n8n-nodes-base.webhook" in types
    assert "n8n-nodes-base.httpRequest" in types
    assert "n8n-nodes-base.if" in types
    assert "n8n-nodes-base.respondToWebhook" in types

    serialized = json.dumps(workflow)
    assert "RELAYDESK_API_URL" in serialized
    assert "/api/v1/process" in serialized
    assert "retryOnFail" in serialized


def test_review_continuation_targets_persisted_review_endpoint() -> None:
    workflow = load_workflow("relaydesk-review-continuation.json")

    assert workflow["name"] == "RelayDesk - Review Continuation"
    serialized = json.dumps(workflow)
    assert "relaydesk/review/continue" in serialized
    assert "/api/v1/workflows/" in serialized
    assert "/review" in serialized
    assert "reviewer_id" in serialized
    assert "edited_response" in serialized
