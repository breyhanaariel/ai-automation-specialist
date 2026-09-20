from datetime import UTC, datetime
from pathlib import Path

from app.persistence import Store
from app.schemas import LeadSubmission, LeadSource
from app.workflow import process_lead


def lead(lead_id: str, email: str = "alex@example.com", company: str = "Northstar Labs", inquiry: str = "Need an automation demo") -> LeadSubmission:
    return LeadSubmission(lead_id=lead_id, full_name="Alex Morgan", email=email, company_name=company,
        source=LeadSource.WEBSITE, received_at=datetime.now(UTC), job_title="VP Operations",
        country="United States", inquiry=inquiry)


def test_workflow_scores_and_preserves_human_outreach_control(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "db.sqlite"))
    result = process_lead(lead("one"), store)
    assert result["score"]["total_score"] >= 80
    assert result["routing"]["route"] == "human_review"
    assert result["outbound_sent"] is False
    assert result["outreach_draft"]


def test_duplicate_routes_to_duplicate_review(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "db.sqlite"))
    process_lead(lead("one"), store)
    result = process_lead(lead("two"), store)
    assert result["routing"]["route"] == "duplicate_review"


def test_spam_is_disqualified(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "db.sqlite"))
    result = process_lead(lead("spam", email="spam@noise-example.com", company="Noise", inquiry="crypto giveaway"), store)
    assert result["routing"]["route"] == "disqualify"
    assert result["outbound_sent"] is False
