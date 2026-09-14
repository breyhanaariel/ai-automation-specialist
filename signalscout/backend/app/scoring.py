from __future__ import annotations

from app.schemas import LeadScore, QualificationBand, ScoreComponent, ScoringWeights


def band_for_score(score: float) -> QualificationBand:
    if score >= 80:
        return QualificationBand.SALES_QUALIFIED
    if score >= 60:
        return QualificationBand.REVIEW
    if score >= 40:
        return QualificationBand.NURTURE
    return QualificationBand.DISQUALIFY


def score_lead(
    *,
    signals: dict[str, float],
    explanations: dict[str, str],
    weights: ScoringWeights,
    config_version: str = "v1",
) -> LeadScore:
    if weights.total() != 100:
        raise ValueError("scoring weights must total 100")

    weight_map = weights.model_dump()
    components: list[ScoreComponent] = []
    total = 0.0

    for name, weight in weight_map.items():
        raw_score = float(signals.get(name, 0.0))
        if not 0 <= raw_score <= 1:
            raise ValueError(f"signal {name} must be between 0 and 1")
        points = round(raw_score * weight, 2)
        total += points
        components.append(
            ScoreComponent(
                name=name,
                raw_score=raw_score,
                weight=weight,
                points=points,
                explanation=explanations.get(name, "No explanation supplied."),
            )
        )

    total = round(total, 2)
    return LeadScore(
        total_score=total,
        band=band_for_score(total),
        components=components,
        config_version=config_version,
    )
