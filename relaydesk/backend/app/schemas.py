from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TicketCategory(StrEnum):
    ACCOUNT_ACCESS = "account_access"
    BILLING = "billing"
    CANCELLATION = "cancellation"
    REFUND = "refund"
    TECHNICAL_ISSUE = "technical_issue"
    PRODUCT_QUESTION = "product_question"
    FEATURE_REQUEST = "feature_request"
    SHIPPING_OR_DELIVERY = "shipping_or_delivery"
    COMPLAINT = "complaint"
    OTHER = "other"


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANGRY = "angry"


class RiskFlag(StrEnum):
    ACCOUNT_SECURITY = "account_security"
    PAYMENT_DISPUTE = "payment_dispute"
    LEGAL_THREAT = "legal_threat"
    SELF_HARM_OR_SAFETY = "self_harm_or_safety"
    ABUSIVE_CONTENT = "abusive_content"
    PRIVACY_REQUEST = "privacy_request"
    CHARGEBACK = "chargeback"
    DATA_LOSS = "data_loss"
    NONE = "none"


class RecommendedRoute(StrEnum):
    AUTO_ELIGIBLE = "auto_eligible"
    HUMAN_VERIFY = "human_verify"
    HUMAN_REVIEW = "human_review"
    MANUAL = "manual"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    EDIT_AND_APPROVE = "edit_and_approve"
    REJECT = "reject"
    ESCALATE = "escalate"


class SupportTicketIn(BaseModel):
    ticket_id: str = Field(min_length=1, max_length=80)
    customer_message: str = Field(min_length=1, max_length=8000)
    received_at: datetime
    customer_id: str | None = Field(default=None, max_length=120)
    customer_name: str | None = Field(default=None, max_length=120)
    account_tier: str | None = Field(default=None, max_length=80)
    prior_ticket_count: int | None = Field(default=None, ge=0)
    source: str | None = Field(default=None, max_length=80)

    @field_validator("customer_message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("customer_message cannot be blank")
        return normalized


class TicketClassification(BaseModel):
    category: TicketCategory
    intent_summary: str = Field(min_length=1, max_length=280)
    priority: Priority
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0)
    risk_flags: list[RiskFlag] = Field(default_factory=lambda: [RiskFlag.NONE])
    recommended_route: RecommendedRoute
    rationale_summary: str = Field(min_length=1, max_length=500)

    @field_validator("risk_flags")
    @classmethod
    def validate_risk_flags(cls, value: list[RiskFlag]) -> list[RiskFlag]:
        unique = list(dict.fromkeys(value))
        if not unique:
            return [RiskFlag.NONE]
        if RiskFlag.NONE in unique and len(unique) > 1:
            unique.remove(RiskFlag.NONE)
        return unique


class RetrievedSource(BaseModel):
    source_id: str
    title: str
    excerpt: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class DraftResponse(BaseModel):
    draft_text: str = Field(min_length=1, max_length=5000)
    source_ids: list[str] = Field(default_factory=list)
    requires_account_action: bool = False
    unsupported_action_claimed: bool = False


class RoutingDecision(BaseModel):
    route: RecommendedRoute
    reason: str
    model_recommendation: RecommendedRoute
    policy_overrode_model: bool = False


class HumanReviewDecision(BaseModel):
    ticket_id: str
    action: ReviewAction
    reviewer_id: str
    reviewed_at: datetime
    edited_response: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=1000)


class AuditEvent(BaseModel):
    event_id: str
    ticket_id: str
    event_type: str
    occurred_at: datetime
    workflow_id: str
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    details: dict[str, object] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    workflow_id: str
    ticket: SupportTicketIn
    classification: TicketClassification | None = None
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    draft: DraftResponse | None = None
    routing: RoutingDecision | None = None
    status: Literal[
        "received",
        "classified",
        "retrieved",
        "drafted",
        "awaiting_review",
        "completed",
        "rejected",
        "escalated",
        "failed",
    ] = "received"
