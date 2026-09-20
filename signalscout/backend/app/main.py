from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.crm import DemoCRM
from app.normalization import normalize_lead
from app.persistence import Store
from app.schemas import HealthResponse, LeadScore, LeadSubmission, ScoringPreviewRequest, ScoringWeights
from app.scoring import score_lead
from app.workflow import process_lead

settings = get_settings()
store = Store(settings.database_url)
app = FastAPI(title=settings.app_name, version="1.0.0")
DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard"
if DASHBOARD.exists():
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD), name="dashboard")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, environment=settings.environment)


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


@app.post("/api/v1/leads/{lead_id}/review")
def review_lead(lead_id: str, action: str) -> dict:
    allowed = {
        "approve": "ready_for_crm",
        "edit_and_approve": "ready_for_crm",
        "nurture": "nurture",
        "disqualify": "disqualify",
    }
    if action not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported review action")
    if not store.update_status(lead_id, allowed[action]):
        raise HTTPException(status_code=404, detail="Lead not found")
    crm = DemoCRM().sync(lead_id) if allowed[action] == "ready_for_crm" else None
    return {
        "lead_id": lead_id,
        "action": action,
        "status": allowed[action],
        "crm": crm.__dict__ if crm else None,
        "outbound_sent": False,
    }


@app.get("/")
def dashboard_home() -> FileResponse:
    return FileResponse(DASHBOARD / "index.html")
