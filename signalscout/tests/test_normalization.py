from datetime import UTC, datetime

from app.normalization import normalize_lead
from app.schemas import LeadSubmission, LeadSource


def test_normalize_lead_cleans_common_fields() -> None:
    lead = LeadSubmission(
        lead_id=" lead-001 ",
        full_name="  Avery   Morgan ",
        email="AVERY@EXAMPLE.COM",
        company_name="  Northstar   Labs ",
        source=LeadSource.WEBSITE,
        received_at=datetime.now(UTC),
        job_title="  VP   Operations ",
        company_domain="https://www.Example.com/about",
        phone="(305) 555-1212",
        inquiry="  Need   workflow automation. ",
    )
    result = normalize_lead(lead)

    assert result.lead.lead_id == "lead-001"
    assert str(result.lead.email) == "avery@example.com"
    assert result.lead.full_name == "Avery Morgan"
    assert result.lead.company_name == "Northstar Labs"
    assert result.lead.job_title == "VP Operations"
    assert result.lead.company_domain == "example.com"
    assert result.lead.phone == "3055551212"
    assert result.lead.inquiry == "Need workflow automation."
    assert result.email_domain == "example.com"
    assert result.normalized_company == "northstar labs"


def test_normalize_lead_uses_email_domain_when_company_domain_missing() -> None:
    lead = LeadSubmission(
        lead_id="lead-002",
        full_name="Jordan Lee",
        email="jordan@acme.test",
        company_name="Acme",
        source=LeadSource.API,
        received_at=datetime.now(UTC),
    )
    result = normalize_lead(lead)
    assert result.lead.company_domain == "acme.test"
