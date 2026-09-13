from __future__ import annotations

from app.config import Settings
from app.schemas import (
    Priority,
    RecommendedRoute,
    RiskFlag,
    Sentiment,
    TicketCategory,
    TicketClassification,
)
from app.services.routing import decide_route


def classification(*, confidence: float, risk_flags: list[RiskFlag], model_route: RecommendedRoute) -> TicketClassification:
    return TicketClassification(
        category=TicketCategory.PRODUCT_QUESTION,
        intent_summary="Customer asks a routine product question.",
        priority=Priority.NORMAL,
        sentiment=Sentiment.NEUTRAL,
        confidence=confidence,
        risk_flags=risk_flags,
        recommended_route=model_route,
        rationale_summary="Routine request.",
    )


def test_high_confidence_no_risk_is_auto_eligible() -> None:
    result = decide_route(
        classification(
            confidence=0.95,
            risk_flags=[RiskFlag.NONE],
            model_route=RecommendedRoute.AUTO_ELIGIBLE,
        ),
        Settings(),
    )
    assert result.route == RecommendedRoute.AUTO_ELIGIBLE
    assert result.policy_overrode_model is False


def test_mid_confidence_requires_human_verification() -> None:
    result = decide_route(
        classification(
            confidence=0.82,
            risk_flags=[RiskFlag.NONE],
            model_route=RecommendedRoute.AUTO_ELIGIBLE,
        ),
        Settings(),
    )
    assert result.route == RecommendedRoute.HUMAN_VERIFY
    assert result.policy_overrode_model is True


def test_low_confidence_goes_manual() -> None:
    result = decide_route(
        classification(
            confidence=0.51,
            risk_flags=[RiskFlag.NONE],
            model_route=RecommendedRoute.HUMAN_VERIFY,
        ),
        Settings(),
    )
    assert result.route == RecommendedRoute.MANUAL


def test_high_risk_overrides_even_high_confidence() -> None:
    result = decide_route(
        classification(
            confidence=0.99,
            risk_flags=[RiskFlag.ACCOUNT_SECURITY],
            model_route=RecommendedRoute.AUTO_ELIGIBLE,
        ),
        Settings(),
    )
    assert result.route == RecommendedRoute.HUMAN_REVIEW
    assert result.policy_overrode_model is True
