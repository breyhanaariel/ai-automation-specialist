from __future__ import annotations

from app.schemas import FinalRoute, QualificationBand, RoutingDecision


def route_lead(*, band: QualificationBand, spam: bool = False, duplicate: bool = False,
               strategic: bool = False, supported_geography: bool = True) -> RoutingDecision:
    if spam:
        return RoutingDecision(route=FinalRoute.DISQUALIFY, score_recommendation=band, reason="Spam/invalid lead.", policy_overrode_score=True)
    if duplicate:
        return RoutingDecision(route=FinalRoute.DUPLICATE_REVIEW, score_recommendation=band, reason="Potential duplicate requires merge/review.", policy_overrode_score=True)
    if strategic:
        return RoutingDecision(route=FinalRoute.HUMAN_REVIEW, score_recommendation=band, reason="Strategic account requires human review.", policy_overrode_score=True)
    if not supported_geography:
        return RoutingDecision(route=FinalRoute.NURTURE, score_recommendation=band, reason="Unsupported geography.", policy_overrode_score=True)
    route = {
        QualificationBand.SALES_QUALIFIED: FinalRoute.HUMAN_REVIEW,
        QualificationBand.REVIEW: FinalRoute.HUMAN_REVIEW,
        QualificationBand.NURTURE: FinalRoute.NURTURE,
        QualificationBand.DISQUALIFY: FinalRoute.DISQUALIFY,
    }[band]
    return RoutingDecision(route=route, score_recommendation=band, reason="Score-band policy.", policy_overrode_score=False)
