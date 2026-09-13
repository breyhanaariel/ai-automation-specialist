from __future__ import annotations

import pytest

from app.providers.demo import DemoProvider
from app.schemas import DraftResponse, RecommendedRoute, RiskFlag, TicketClassification


@pytest.mark.asyncio
async def test_demo_provider_routes_account_security_to_human_review() -> None:
    provider = DemoProvider()
    result = await provider.generate_structured(
        system_prompt="classify",
        user_prompt="Customer message:\nSomeone logged into my account and changed my password.",
        response_model=TicketClassification,
    )

    assert result.recommended_route == RecommendedRoute.HUMAN_REVIEW
    assert RiskFlag.ACCOUNT_SECURITY in result.risk_flags
    assert result.confidence >= 0.90


@pytest.mark.asyncio
async def test_demo_provider_draft_only_cites_supplied_source_ids() -> None:
    provider = DemoProvider()
    result = await provider.generate_structured(
        system_prompt="draft",
        user_prompt=(
            "Customer message: How do I reset my password?\n"
            "Knowledge sources:\n[kb-password-reset] Password reset\nUse reset email."
        ),
        response_model=DraftResponse,
    )

    assert result.source_ids == ["kb-password-reset"]
    assert result.unsupported_action_claimed is False
