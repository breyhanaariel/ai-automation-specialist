import pytest

from app.schemas import QualificationBand, ScoringWeights
from app.scoring import band_for_score, score_lead


def test_default_weights_total_100() -> None:
    assert ScoringWeights().total() == 100


def test_band_boundaries() -> None:
    assert band_for_score(80) == QualificationBand.SALES_QUALIFIED
    assert band_for_score(79.99) == QualificationBand.REVIEW
    assert band_for_score(60) == QualificationBand.REVIEW
    assert band_for_score(40) == QualificationBand.NURTURE
    assert band_for_score(39.99) == QualificationBand.DISQUALIFY


def test_score_is_deterministic_and_explainable() -> None:
    signals = {
        "company_fit": 1.0,
        "role_fit": 0.75,
        "intent": 0.8,
        "data_quality": 1.0,
        "geography": 1.0,
        "source_quality": 0.8,
    }
    explanations = {name: f"Evidence for {name}." for name in signals}
    first = score_lead(signals=signals, explanations=explanations, weights=ScoringWeights())
    second = score_lead(signals=signals, explanations=explanations, weights=ScoringWeights())
    assert first == second
    assert first.total_score == 89.0
    assert first.band == QualificationBand.SALES_QUALIFIED
    assert len(first.components) == 6


def test_weights_must_total_100() -> None:
    weights = ScoringWeights(company_fit=20)
    with pytest.raises(ValueError, match="must total 100"):
        score_lead(signals={}, explanations={}, weights=weights)
