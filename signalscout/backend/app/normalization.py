from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import LeadSubmission


_whitespace = re.compile(r"\s+")
_non_digits_plus = re.compile(r"[^\d+]")


@dataclass(frozen=True)
class NormalizedLead:
    lead: LeadSubmission
    email_domain: str
    normalized_company: str


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = _whitespace.sub(" ", value).strip()
    return value or None


def _normalize_domain(value: str | None, email_domain: str) -> str:
    domain = (value or email_domain).strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/", 1)[0]
    return domain.removeprefix("www.")


def normalize_lead(lead: LeadSubmission) -> NormalizedLead:
    email = str(lead.email).strip().lower()
    email_domain = email.rsplit("@", 1)[1]
    company = _whitespace.sub(" ", lead.company_name).strip()
    phone = _clean_optional(lead.phone)
    if phone:
        phone = _non_digits_plus.sub("", phone)

    normalized = lead.model_copy(
        update={
            "lead_id": lead.lead_id.strip(),
            "full_name": _whitespace.sub(" ", lead.full_name).strip(),
            "email": email,
            "company_name": company,
            "job_title": _clean_optional(lead.job_title),
            "company_domain": _normalize_domain(lead.company_domain, email_domain),
            "phone": phone,
            "country": _clean_optional(lead.country),
            "inquiry": _clean_optional(lead.inquiry),
        }
    )
    return NormalizedLead(
        lead=normalized,
        email_domain=email_domain,
        normalized_company=company.casefold(),
    )
