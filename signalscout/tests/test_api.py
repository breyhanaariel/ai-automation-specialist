from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == "SignalScout"


def test_default_scoring_weights() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/scoring/defaults")
    assert response.status_code == 200
    assert sum(response.json().values()) == 100


def test_preview_scoring_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/scoring/preview",
        json={
            "company_fit": 1,
            "role_fit": 1,
            "intent": 1,
            "data_quality": 1,
            "geography": 1,
            "source_quality": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["total_score"] == 100
    assert response.json()["band"] == "sales_qualified"
