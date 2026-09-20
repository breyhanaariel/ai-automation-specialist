from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class EnrichmentResult:
    industry: str
    company_size: str
    location: str
    role_relevance: float
    data_quality: float
    company_summary: str


@dataclass(frozen=True)
class AnalysisResult:
    intent: float
    role_fit: float
    rationale: str


class DemoEnrichmentProvider:
    name = "demo"

    def enrich(self, *, company: str, title: str | None, country: str | None) -> EnrichmentResult:
        title_text = (title or "").lower()
        role = 1.0 if any(x in title_text for x in ("owner", "founder", "chief", "vp", "director", "head")) else 0.65
        return EnrichmentResult(
            industry="Business Services",
            company_size="11-200",
            location=country or "Unknown",
            role_relevance=role,
            data_quality=0.9 if title and country else 0.7,
            company_summary=f"{company} is a synthetic demo company used for SignalScout evaluation.",
        )


class DemoAIProvider:
    name = "demo"
    model = "deterministic-demo-v1"

    def analyze(self, *, inquiry: str | None, title: str | None) -> AnalysisResult:
        text = f"{inquiry or ''} {title or ''}".lower()
        high = ("quote", "proposal", "demo", "buy", "implement", "automation", "crm")
        low = ("student", "job", "free", "spam")
        intent = 0.9 if any(x in text for x in high) else 0.35 if any(x in text for x in low) else 0.6
        role_fit = 0.9 if re.search(r"\b(owner|founder|chief|vp|director|head)\b", text) else 0.6
        return AnalysisResult(intent=intent, role_fit=role_fit, rationale="Deterministic demo analysis; not an LLM.")


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://127.0.0.1:11434") -> None:
        self.model = model
        self.base_url = base_url

    def analyze(self, *, inquiry: str | None, title: str | None) -> AnalysisResult:
        import httpx
        prompt = (
            "Return JSON only with intent and role_fit numbers from 0 to 1 and rationale. "
            f"Title: {title or ''}\nInquiry: {inquiry or ''}"
        )
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "format": "json", "stream": False},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        import json
        parsed = json.loads(data["response"])
        return AnalysisResult(
            intent=max(0.0, min(1.0, float(parsed["intent"]))),
            role_fit=max(0.0, min(1.0, float(parsed["role_fit"]))),
            rationale=str(parsed.get("rationale", "Ollama analysis.")),
        )
