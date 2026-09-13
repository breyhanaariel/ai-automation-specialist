from __future__ import annotations

import re

from app.providers.base import LLMProvider, T
from app.schemas import (
    DraftResponse,
    Priority,
    RecommendedRoute,
    RiskFlag,
    Sentiment,
    TicketCategory,
    TicketClassification,
)


class DemoProvider(LLMProvider):
    """Deterministic zero-cost provider for the public portfolio demo.

    This intentionally does not pretend to be an LLM. It keeps the deployed
    demo usable without paid API keys while local development uses Ollama.
    """

    name = "demo"
    model = "deterministic-demo-v1"

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        if response_model is TicketClassification:
            return response_model.model_validate(self._classify(user_prompt).model_dump())
        if response_model is DraftResponse:
            return response_model.model_validate(self._draft(user_prompt).model_dump())
        raise ValueError(f"DemoProvider does not support {response_model.__name__}")

    def _classify(self, prompt: str) -> TicketClassification:
        text = prompt.lower()
        category = TicketCategory.OTHER
        priority = Priority.NORMAL
        sentiment = Sentiment.NEUTRAL
        risk_flags: list[RiskFlag] = []
        confidence = 0.84

        rules = [
            (("password", "login", "account"), TicketCategory.ACCOUNT_ACCESS),
            (("refund",), TicketCategory.REFUND),
            (("cancel", "cancellation"), TicketCategory.CANCELLATION),
            (("invoice", "charged", "billing", "card"), TicketCategory.BILLING),
            (("crash", "bug", "error", "not work"), TicketCategory.TECHNICAL_ISSUE),
            (("feature", "please add"), TicketCategory.FEATURE_REQUEST),
            (("shipping", "delivered", "package"), TicketCategory.SHIPPING_OR_DELIVERY),
            (("how do", "where can", "do you support", "can i"), TicketCategory.PRODUCT_QUESTION),
        ]
        for keywords, candidate in rules:
            if any(keyword in text for keyword in keywords):
                category = candidate
                confidence = 0.94
                break

        risk_rules = [
            (("hacked", "someone logged", "password changed"), RiskFlag.ACCOUNT_SECURITY),
            (("charged twice", "wrong charge", "billing dispute"), RiskFlag.PAYMENT_DISPUTE),
            (("chargeback",), RiskFlag.CHARGEBACK),
            (("lawyer", "attorney general", "legal"), RiskFlag.LEGAL_THREAT),
            (("delete all personal", "privacy"), RiskFlag.PRIVACY_REQUEST),
            (("deleted", "data loss", "restore"), RiskFlag.DATA_LOSS),
        ]
        for keywords, flag in risk_rules:
            if any(keyword in text for keyword in keywords):
                risk_flags.append(flag)

        if risk_flags:
            priority = Priority.URGENT if RiskFlag.ACCOUNT_SECURITY in risk_flags else Priority.HIGH
            sentiment = Sentiment.NEGATIVE
            route = RecommendedRoute.HUMAN_REVIEW
            confidence = max(confidence, 0.95)
        elif category in {TicketCategory.PRODUCT_QUESTION, TicketCategory.FEATURE_REQUEST}:
            priority = Priority.LOW
            route = RecommendedRoute.AUTO_ELIGIBLE
        elif category is TicketCategory.OTHER:
            confidence = 0.55
            route = RecommendedRoute.MANUAL
        else:
            route = RecommendedRoute.HUMAN_VERIFY

        return TicketClassification(
            category=category,
            intent_summary=f"Demo classification for {category.value.replace('_', ' ')} request.",
            priority=priority,
            sentiment=sentiment,
            confidence=confidence,
            risk_flags=risk_flags or [RiskFlag.NONE],
            recommended_route=route,
            rationale_summary="Deterministic public-demo rules; local Ollama provides real model inference.",
        )

    def _draft(self, prompt: str) -> DraftResponse:
        source_ids = re.findall(r"\[(kb-[^\]]+)\]", prompt)
        requires_action = any(
            token in prompt.lower()
            for token in ("refund", "cancel", "account", "invoice", "privacy", "shipping")
        )
        if source_ids:
            draft_text = (
                "Thanks for reaching out. Based on the available support guidance, "
                "I can help with the next documented step. If an account-specific action "
                "is required, a support agent will review it before anything changes."
            )
        else:
            draft_text = (
                "Thanks for reaching out. I do not have enough verified support guidance "
                "to answer this safely, so I am routing it for human review."
            )
        return DraftResponse(
            draft_text=draft_text,
            source_ids=list(dict.fromkeys(source_ids)),
            requires_account_action=requires_action,
            unsupported_action_claimed=False,
        )
