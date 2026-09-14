from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field, field_validator


class LeadSource(StrEnum):
    WEBSITE = "website"
    CSV = "csv"
    API = "api"
    PARTNER = "partner"


class QualificationBand(StrEnum):
    SALES_QUALIFIED = "sales_qualified"
    REVIEW = "review"
    NURTURE = "nurture"
    DISQUALIFY = "disqualify"


class FinalRoute(StrEnum):
    READY_FOR_CRM = "ready_for_crm"
    HUMAN_REVIEW = "human_review"
    NURTURE = "nurture"
    DISQUALIFY = "disqualify"
    DUPLICATE_REVIEW = "duplicate_review"


class LeadSubmission(BaseModel):
    lead_id: str = Field(min_length=1, max_length=120)
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    company_name: str = Field(min_length=1, max_length=200)
    source: LeadSource
    received_at: datetime
    job_title: str | None = Field(default=None, max_length=200)
    company_domain: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=120)
    inquiry: str | None = Field(default=None, max_length=5000)

    @field_validator("lead_id", "full_name", "company_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class ScoringWeights(BaseModel):
    company_fit: int = 30
    role_fit: int = 20
    intent: int = 25
    data_quality: int = 10
    geography: int = 10
    source_quality: int = 5

    def total(self) -> int:
        return sum(self.model_dump().values())

    @field_validator(
        "company_fit",
        "role_fit",
        "intent",
        "data_quality",
        "geography",
        "source_quality",
    )
    @classmethod
    def validate_weight(cls, value: int) -> int:
        if not 0 <= value <= 100:
            raise ValueError("weight must be between 0 and 100")
        return value


class ScoreComponent(BaseModel):
    name: str
    raw_score: float = Field(ge=0, le=1)
    weight: int = Field(ge=0, le=100)
    points: float = Field(ge=0, le=100)
    explanation: str


class LeadScore(BaseModel):
    total_score: float = Field(ge=0, le=100)
    band: QualificationBand
    components: list[ScoreComponent]
    config_version: str


class RoutingDecision(BaseModel):
    route: FinalRoute
    score_recommendation: QualificationBand
    reason: str
    policy_overrode_score: bool = False


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
