from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.schemas import (
    HealthResponse,
    LeadScore,
    LeadSubmission,
    ScoringPreviewRequest,
    ScoringWeights,
)
from app.normalization import normalize_lead
from app.scoring import score_lead
from app.persistence import Store
from app.workflow import process_lead

settings = get_settings()
store = Store()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
    )


@app.post("/api/v1/leads/normalize", response_model=LeadSubmission)
def normalize_lead_endpoint(lead: LeadSubmission) -> LeadSubmission:
    return normalize_lead(lead).lead


@app.get("/api/v1/scoring/defaults", response_model=ScoringWeights)
def scoring_defaults() -> ScoringWeights:
    return ScoringWeights()


@app.post("/api/v1/scoring/preview", response_model=LeadScore)
def preview_score(request: ScoringPreviewRequest) -> LeadScore:
    resolved_weights = request.weights or ScoringWeights()
    explanations = {name: "Preview signal." for name in resolved_weights.model_dump()}
    try:
        return score_lead(
            signals=request.signals,
            explanations=explanations,
            weights=resolved_weights,
            config_version="preview-v1",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/leads/process")
def process_lead_endpoint(lead: LeadSubmission) -> dict:
    return process_lead(lead, store)


@app.get("/api/v1/leads")
def list_leads() -> list[dict]:
    return store.list()


@app.get("/api/v1/metrics")
def metrics() -> dict:
    return store.metrics()
