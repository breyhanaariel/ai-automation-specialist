from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.persistence import WorkflowRepository
from app.providers.base import ProviderError
from app.providers.factory import build_provider
from app.schemas import (
    AuditEvent,
    RecommendedRoute,
    RoutingDecision,
    SupportTicketIn,
    TicketClassification,
    WorkflowState,
)
from app.services.classification import ClassificationService
from app.services.drafting import DraftingService
from app.services.retrieval import KnowledgeRetriever
from app.services.routing import decide_route

router = APIRouter(prefix="/api/v1", tags=["classification"])


def get_repository(settings: Annotated[Settings, Depends(get_settings)]) -> WorkflowRepository:
    return WorkflowRepository(settings.database_url)


def audit_event(
    *,
    workflow_id: str,
    ticket_id: str,
    event_type: str,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
    details: dict[str, object] | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id=str(uuid4()),
        ticket_id=ticket_id,
        event_type=event_type,
        occurred_at=datetime.now(UTC),
        workflow_id=workflow_id,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        details=details or {},
    )


@router.post("/classify")
async def classify_ticket(
    ticket: SupportTicketIn,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, TicketClassification | RoutingDecision | str]:
    provider = build_provider(settings)
    service = ClassificationService(provider)

    try:
        classification = await service.classify(ticket)
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.__class__.__name__, "message": str(exc)},
        ) from exc

    routing = decide_route(classification, settings)
    return {
        "ticket_id": ticket.ticket_id,
        "provider": provider.name,
        "model": provider.model,
        "classification": classification,
        "routing": routing,
    }


@router.post("/process")
async def process_ticket(
    ticket: SupportTicketIn,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[WorkflowRepository, Depends(get_repository)],
) -> dict[str, object]:
    provider = build_provider(settings)
    classifier = ClassificationService(provider)
    retriever = KnowledgeRetriever()
    drafter = DraftingService(provider)
    workflow_id = str(uuid4())
    started = perf_counter()

    state = WorkflowState(workflow_id=workflow_id, ticket=ticket)
    repository.save_workflow(state)
    repository.add_audit_event(
        audit_event(
            workflow_id=workflow_id,
            ticket_id=ticket.ticket_id,
            event_type="workflow_received",
            provider=provider.name,
            model=provider.model,
        )
    )

    try:
        classification = await classifier.classify(ticket)
        state.classification = classification
        state.status = "classified"
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="ticket_classified",
                provider=provider.name,
                model=provider.model,
                details={
                    "category": classification.category.value,
                    "confidence": classification.confidence,
                },
            )
        )

        sources = retriever.retrieve(ticket, classification)
        state.retrieved_sources = sources
        state.status = "retrieved"
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="knowledge_retrieved",
                details={"source_ids": [source.source_id for source in sources]},
            )
        )

        draft = await drafter.draft(ticket, classification, sources)
        state.draft = draft
        state.status = "drafted"
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="response_drafted",
                provider=provider.name,
                model=provider.model,
                details={"source_ids": draft.source_ids},
            )
        )
    except ProviderError as exc:
        state.status = "failed"
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="workflow_failed",
                provider=provider.name,
                model=provider.model,
                details={"error_type": exc.__class__.__name__, "message": str(exc)},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.__class__.__name__, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        state.status = "failed"
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="workflow_failed",
                details={"error_type": "GroundingValidationError", "message": str(exc)},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "GroundingValidationError", "message": str(exc)},
        ) from exc

    routing = decide_route(classification, settings)
    if draft.unsupported_action_claimed:
        routing = RoutingDecision(
            route=RecommendedRoute.HUMAN_REVIEW,
            reason="Draft flagged an unsupported external-action claim.",
            model_recommendation=routing.model_recommendation,
            policy_overrode_model=True,
        )

    state.routing = routing
    state.status = (
        "completed" if routing.route == RecommendedRoute.AUTO_ELIGIBLE else "awaiting_review"
    )
    repository.save_workflow(state)

    latency_ms = int((perf_counter() - started) * 1000)
    repository.add_audit_event(
        audit_event(
            workflow_id=workflow_id,
            ticket_id=ticket.ticket_id,
            event_type="workflow_completed",
            provider=provider.name,
            model=provider.model,
            latency_ms=latency_ms,
            details={"route": routing.route.value, "status": state.status},
        )
    )

    return {
        "workflow_id": workflow_id,
        "ticket_id": ticket.ticket_id,
        "provider": provider.name,
        "model": provider.model,
        "classification": classification,
        "sources": sources,
        "draft": draft,
        "routing": routing,
        "status": state.status,
        "latency_ms": latency_ms,
    }


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    repository: Annotated[WorkflowRepository, Depends(get_repository)],
) -> WorkflowState:
    state = repository.get_workflow(workflow_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return state


@router.get("/workflows/{workflow_id}/audit")
async def get_workflow_audit(
    workflow_id: str,
    repository: Annotated[WorkflowRepository, Depends(get_repository)],
) -> list[AuditEvent]:
    if repository.get_workflow(workflow_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return repository.list_audit_events(workflow_id)


@router.get("/metrics")
async def get_metrics(
    repository: Annotated[WorkflowRepository, Depends(get_repository)],
) -> dict[str, int | float]:
    return repository.metrics()
