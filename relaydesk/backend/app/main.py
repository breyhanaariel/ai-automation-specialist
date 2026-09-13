from __future__ import annotations

from fastapi import FastAPI

from app.api import router
from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Human-aware AI customer support triage and routing API.",
)
app.include_router(router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }
