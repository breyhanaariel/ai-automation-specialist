from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.schemas import HealthResponse, LeadScore, ScoringWeights
from app.scoring import score_lead

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
    )


@app.get("/api/v1/scoring/defaults", response_model=ScoringWeights)
def scoring_defaults() -> ScoringWeights:
    return ScoringWeights()


@app.post("/api/v1/scoring/preview", response_model=LeadScore)
def preview_score(
    signals: dict[str, float],
    weights: ScoringWeights | None = None,
) -> LeadScore:
    resolved_weights = weights or ScoringWeights()
    explanations = {name: "Preview signal." for name in resolved_weights.model_dump()}
    try:
        return score_lead(
            signals=signals,
            explanations=explanations,
            weights=resolved_weights,
            config_version="preview-v1",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
