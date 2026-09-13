from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.providers.base import ProviderError
from app.providers.factory import build_provider
from app.schemas import RoutingDecision, SupportTicketIn, TicketClassification
from app.services.classification import ClassificationService
from app.services.routing import decide_route

router = APIRouter(prefix="/api/v1", tags=["classification"])


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
