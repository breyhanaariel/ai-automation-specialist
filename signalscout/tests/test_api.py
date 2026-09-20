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
            "signals": {
                "company_fit": 1,
                "role_fit": 1,
                "intent": 1,
                "data_quality": 1,
                "geography": 1,
                "source_quality": 1,
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["total_score"] == 100
    assert response.json()["band"] == "sales_qualified"


def test_normalize_lead_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/leads/normalize",
        json={
            "lead_id": "web-001",
            "full_name": "  Avery   Morgan ",
            "email": "AVERY@EXAMPLE.COM",
            "company_name": " Northstar   Labs ",
            "source": "website",
            "received_at": "2026-09-20T12:00:00Z",
            "company_domain": "https://www.example.com/about",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Avery Morgan"
    assert body["email"] == "avery@example.com"
    assert body["company_name"] == "Northstar Labs"
    assert body["company_domain"] == "example.com"
