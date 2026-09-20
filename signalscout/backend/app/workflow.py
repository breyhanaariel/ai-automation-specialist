from __future__ import annotations

from app.normalization import normalize_lead
from app.persistence import Store
from app.providers import DemoAIProvider, DemoEnrichmentProvider
from app.routing import route_lead
from app.schemas import LeadSubmission, ScoringWeights
from app.scoring import score_lead


SUPPORTED_COUNTRIES = {"united states", "usa", "us", "canada", "united kingdom", "uk"}


def process_lead(lead: LeadSubmission, store: Store) -> dict:
    n = normalize_lead(lead)
    duplicate = store.find_duplicate(str(n.lead.email), n.lead.company_name, n.lead.lead_id)
    enrichment = DemoEnrichmentProvider().enrich(
        company=n.lead.company_name, title=n.lead.job_title, country=n.lead.country
    )
    analysis = DemoAIProvider().analyze(inquiry=n.lead.inquiry, title=n.lead.job_title)
    inquiry = (n.lead.inquiry or "").lower()
    spam = any(x in inquiry for x in ("buy followers", "crypto giveaway", "casino spam"))
    strategic = any(x in n.lead.company_name.lower() for x in ("enterprise", "global", "strategic"))
    supported = not n.lead.country or n.lead.country.lower() in SUPPORTED_COUNTRIES
    signals = {
        "company_fit": 0.85,
        "role_fit": analysis.role_fit,
        "intent": analysis.intent,
        "data_quality": enrichment.data_quality,
        "geography": 1.0 if supported else 0.0,
        "source_quality": 0.9 if n.lead.source.value in ("website", "partner") else 0.75,
    }
    explanations = {k: f"{k.replace('_',' ').title()} signal." for k in signals}
    score = score_lead(signals=signals, explanations=explanations, weights=ScoringWeights(), config_version="default-v1")
    decision = route_lead(band=score.band, spam=spam, duplicate=duplicate, strategic=strategic, supported_geography=supported)
    result = {
        "lead": n.lead.model_dump(mode="json"),
        "enrichment": enrichment.__dict__,
        "analysis": analysis.__dict__,
        "score": score.model_dump(mode="json"),
        "routing": decision.model_dump(mode="json"),
        "outreach_draft": None if decision.route.value == "disqualify" else (
            f"Hi {n.lead.full_name.split()[0]}, thanks for reaching out to SignalScout's fictional demo company. "
            "A sales representative can review your automation goals and follow up."
        ),
        "outbound_sent": False,
    }
    store.save(n.lead.lead_id, str(n.lead.email), n.lead.company_name, decision.route.value, result)
    return result
