from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated, TypeVar
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.config import Settings, get_settings
from app.persistence import WorkflowRepository
from app.persistence_postgres import PostgresWorkflowRepository
from app.providers.base import (
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.factory import build_provider
from app.schemas import (
    AuditEvent,
    HumanReviewDecision,
    RecommendedRoute,
    ReviewAction,
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
R = TypeVar("R")
Repository = WorkflowRepository | PostgresWorkflowRepository


def get_repository(settings: Annotated[Settings, Depends(get_settings)]) -> Repository:
    if settings.database_url.startswith(("postgres://", "postgresql://")):
        return PostgresWorkflowRepository(settings.database_url)
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


async def with_retry(
    operation: Callable[[], Awaitable[R]],
    *,
    max_retries: int,
    on_retry: Callable[[ProviderError, int], None],
) -> R:
    attempt = 0
    while True:
        try:
            return await operation()
        except (ProviderTimeoutError, ProviderUnavailableError) as exc:
            if attempt >= max_retries:
                raise
            attempt += 1
            on_retry(exc, attempt)


def workflow_response(
    state: WorkflowState,
    *,
    idempotent_replay: bool = False,
) -> dict[str, object]:
    return {
        "workflow_id": state.workflow_id,
        "ticket_id": state.ticket.ticket_id,
        "correlation_id": state.correlation_id or state.workflow_id,
        "provider": state.provider,
        "model": state.model,
        "classification": state.classification,
        "sources": state.retrieved_sources,
        "draft": state.draft,
        "routing": state.routing,
        "status": state.status,
        "stage_latencies_ms": state.stage_latencies_ms,
        "latency_ms": state.stage_latencies_ms.get("total", 0),
        "retry_count": state.retry_count,
        "error_code": state.error_code,
        "idempotent_replay": idempotent_replay,
    }


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
    repository: Annotated[Repository, Depends(get_repository)],
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> dict[str, object]:
    workflow_id = str(uuid4())
    claimed_by = repository.claim_ticket(ticket.ticket_id, workflow_id)
    if claimed_by is not None:
        existing = repository.get_workflow(claimed_by)
        if existing is None:
            existing = repository.get_workflow_by_ticket(ticket.ticket_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "IdempotencyConflict",
                    "message": "Ticket is already being processed",
                },
            )
        repository.add_audit_event(
            audit_event(
                workflow_id=existing.workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="idempotent_replay",
                details={"correlation_id": correlation_id or ""},
            )
        )
        return workflow_response(existing, idempotent_replay=True)

    provider = build_provider(settings)
    classifier = ClassificationService(provider)
    retriever = KnowledgeRetriever()
    drafter = DraftingService(provider)
    started = perf_counter()
    resolved_correlation_id = correlation_id or workflow_id
    state = WorkflowState(
        workflow_id=workflow_id,
        ticket=ticket,
        correlation_id=resolved_correlation_id,
        provider=provider.name,
        model=provider.model,
    )
    repository.save_workflow(state)
    repository.add_audit_event(
        audit_event(
            workflow_id=workflow_id,
            ticket_id=ticket.ticket_id,
            event_type="workflow_received",
            provider=provider.name,
            model=provider.model,
            details={"correlation_id": resolved_correlation_id},
        )
    )

    def record_retry(exc: ProviderError, attempt: int) -> None:
        state.retry_count += 1
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="provider_retry",
                provider=provider.name,
                model=provider.model,
                details={
                    "attempt": attempt,
                    "error_code": exc.__class__.__name__,
                    "correlation_id": resolved_correlation_id,
                },
            )
        )

    try:
        stage_started = perf_counter()
        classification = await with_retry(
            lambda: classifier.classify(ticket),
            max_retries=settings.llm_max_retries,
            on_retry=record_retry,
        )
        state.stage_latencies_ms["classification"] = int(
            (perf_counter() - stage_started) * 1000
        )
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
                latency_ms=state.stage_latencies_ms["classification"],
                details={
                    "category": classification.category.value,
                    "confidence": classification.confidence,
                },
            )
        )

        stage_started = perf_counter()
        sources = retriever.retrieve(ticket, classification)
        state.stage_latencies_ms["retrieval"] = int(
            (perf_counter() - stage_started) * 1000
        )
        state.retrieved_sources = sources
        state.status = "retrieved"
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="knowledge_retrieved",
                latency_ms=state.stage_latencies_ms["retrieval"],
                details={"source_ids": [source.source_id for source in sources]},
            )
        )

        stage_started = perf_counter()
        draft = await with_retry(
            lambda: drafter.draft(ticket, classification, sources),
            max_retries=settings.llm_max_retries,
            on_retry=record_retry,
        )
        state.stage_latencies_ms["drafting"] = int(
            (perf_counter() - stage_started) * 1000
        )
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
                latency_ms=state.stage_latencies_ms["drafting"],
                details={"source_ids": draft.source_ids},
            )
        )
    except ProviderError as exc:
        state.status = "failed"
        state.error_code = exc.__class__.__name__
        state.error_message = str(exc)
        state.stage_latencies_ms["total"] = int((perf_counter() - started) * 1000)
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="workflow_failed",
                provider=provider.name,
                model=provider.model,
                latency_ms=state.stage_latencies_ms["total"],
                details={
                    "error_code": state.error_code,
                    "message": state.error_message,
                    "retry_count": state.retry_count,
                    "correlation_id": resolved_correlation_id,
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": state.error_code,
                "message": state.error_message,
                "workflow_id": workflow_id,
            },
        ) from exc
    except ValueError as exc:
        state.status = "failed"
        state.error_code = "GroundingValidationError"
        state.error_message = str(exc)
        state.stage_latencies_ms["total"] = int((perf_counter() - started) * 1000)
        repository.save_workflow(state)
        repository.add_audit_event(
            audit_event(
                workflow_id=workflow_id,
                ticket_id=ticket.ticket_id,
                event_type="workflow_failed",
                latency_ms=state.stage_latencies_ms["total"],
                details={
                    "error_code": state.error_code,
                    "message": state.error_message,
                },
            )
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": state.error_code,
                "message": state.error_message,
                "workflow_id": workflow_id,
            },
        ) from exc

    routing = decide_route(classification, settings)
    if draft.unsupported_action_claimed:
        routing = RoutingDecision(
            route=RecommendedRoute.HUMAN_REVIEW,
            reason="Draft flagged an unsupported external-action claim.",
            model_recommendation=routing.model_recommendation,
            policy_overrode_model=True,
        )
    elif draft.requires_account_action:
        routing = RoutingDecision(
            route=RecommendedRoute.HUMAN_REVIEW,
            reason="Account-changing action requires human approval before execution.",
            model_recommendation=routing.model_recommendation,
            policy_overrode_model=True,
        )

    state.routing = routing
    state.status = (
        "ready_for_action"
        if routing.route == RecommendedRoute.AUTO_ELIGIBLE
        else "awaiting_review"
    )
    state.stage_latencies_ms["total"] = int((perf_counter() - started) * 1000)
    repository.save_workflow(state)
    repository.add_audit_event(
        audit_event(
            workflow_id=workflow_id,
            ticket_id=ticket.ticket_id,
            event_type="workflow_routed",
            provider=provider.name,
            model=provider.model,
            latency_ms=state.stage_latencies_ms["total"],
            details={
                "route": routing.route.value,
                "status": state.status,
                "retry_count": state.retry_count,
                "correlation_id": resolved_correlation_id,
            },
        )
    )
    return workflow_response(state)


@router.get("/workflows")
async def list_workflows(
    repository: Annotated[Repository, Depends(get_repository)],
    workflow_status: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[WorkflowState]:
    return repository.list_workflows(status=workflow_status, limit=limit)


@router.post("/workflows/{workflow_id}/review")
async def review_workflow(
    workflow_id: str,
    decision: HumanReviewDecision,
    repository: Annotated[Repository, Depends(get_repository)],
) -> dict[str, object]:
    state = repository.get_workflow(workflow_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    if state.status != "awaiting_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Workflow is not awaiting review; "
                f"current status is {state.status}"
            ),
        )
    if decision.ticket_id != state.ticket.ticket_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Review ticket_id does not match workflow ticket_id",
        )
    if decision.action == ReviewAction.EDIT_AND_APPROVE and not decision.edited_response:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="edited_response is required for edit_and_approve",
        )

    if decision.action == ReviewAction.EDIT_AND_APPROVE and state.draft is not None:
        state.draft.draft_text = decision.edited_response or state.draft.draft_text
    if decision.action in {ReviewAction.APPROVE, ReviewAction.EDIT_AND_APPROVE}:
        state.status = "ready_for_action"
    elif decision.action == ReviewAction.REJECT:
        state.status = "rejected"
    else:
        state.status = "escalated"

    repository.save_workflow(state)
    repository.add_audit_event(
        audit_event(
            workflow_id=workflow_id,
            ticket_id=state.ticket.ticket_id,
            event_type="human_review_decided",
            details={
                "action": decision.action.value,
                "reviewer_id": decision.reviewer_id,
                "reviewed_at": decision.reviewed_at.isoformat(),
                "notes": decision.notes or "",
                "edited": decision.action == ReviewAction.EDIT_AND_APPROVE,
                "resulting_status": state.status,
                "correlation_id": state.correlation_id or "",
            },
        )
    )
    return {
        "workflow_id": workflow_id,
        "ticket_id": state.ticket.ticket_id,
        "action": decision.action,
        "status": state.status,
        "draft": state.draft,
    }


@router.post("/workflows/{workflow_id}/complete")
async def complete_workflow(
    workflow_id: str,
    repository: Annotated[Repository, Depends(get_repository)],
) -> dict[str, object]:
    state = repository.get_workflow(workflow_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    if state.status != "ready_for_action":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow is not ready for action; current status is {state.status}",
        )
    state.status = "completed"
    repository.save_workflow(state)
    repository.add_audit_event(
        audit_event(
            workflow_id=workflow_id,
            ticket_id=state.ticket.ticket_id,
            event_type="workflow_completed",
            provider=state.provider,
            model=state.model,
            details={"correlation_id": state.correlation_id or ""},
        )
    )
    return workflow_response(state)


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    repository: Annotated[Repository, Depends(get_repository)],
) -> WorkflowState:
    state = repository.get_workflow(workflow_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return state


@router.get("/workflows/{workflow_id}/audit")
async def get_workflow_audit(
    workflow_id: str,
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[AuditEvent]:
    if repository.get_workflow(workflow_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return repository.list_audit_events(workflow_id)


@router.get("/metrics")
async def get_metrics(
    repository: Annotated[Repository, Depends(get_repository)],
) -> dict[str, int | float]:
    return repository.metrics()
