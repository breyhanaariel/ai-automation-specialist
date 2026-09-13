from __future__ import annotations

from app.config import Settings
from app.schemas import RecommendedRoute, RiskFlag, RoutingDecision, TicketClassification


HIGH_RISK_FLAGS = {
    RiskFlag.ACCOUNT_SECURITY,
    RiskFlag.PAYMENT_DISPUTE,
    RiskFlag.LEGAL_THREAT,
    RiskFlag.SELF_HARM_OR_SAFETY,
    RiskFlag.PRIVACY_REQUEST,
    RiskFlag.CHARGEBACK,
    RiskFlag.DATA_LOSS,
}


def decide_route(
    classification: TicketClassification,
    settings: Settings,
) -> RoutingDecision:
    model_route = classification.recommended_route
    active_risks = set(classification.risk_flags) - {RiskFlag.NONE}

    if active_risks & HIGH_RISK_FLAGS:
        route = RecommendedRoute.HUMAN_REVIEW
        reason = "High-risk flag requires human review regardless of model confidence."
    elif classification.confidence >= settings.classification_auto_threshold:
        route = RecommendedRoute.AUTO_ELIGIBLE
        reason = (
            f"Confidence {classification.confidence:.2f} meets the automatic-processing "
            f"threshold {settings.classification_auto_threshold:.2f} and no high-risk flag is present."
        )
    elif classification.confidence >= settings.classification_review_threshold:
        route = RecommendedRoute.HUMAN_VERIFY
        reason = (
            f"Confidence {classification.confidence:.2f} is below the automatic threshold but "
            f"meets the verification threshold {settings.classification_review_threshold:.2f}."
        )
    else:
        route = RecommendedRoute.MANUAL
        reason = (
            f"Confidence {classification.confidence:.2f} is below the verification threshold "
            f"{settings.classification_review_threshold:.2f}."
        )

    return RoutingDecision(
        route=route,
        reason=reason,
        model_recommendation=model_route,
        policy_overrode_model=route != model_route,
    )
