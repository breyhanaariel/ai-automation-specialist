from app.providers.base import LLMProvider
from app.schemas import (
    DraftResponse,
    RetrievedSource,
    SupportTicketIn,
    TicketClassification,
)

DRAFT_SYSTEM_PROMPT = """You are RelayDesk's grounded customer-support drafting assistant.
Use only the supplied knowledge sources and ticket context.

Rules:
- Do not claim any refund, cancellation, replacement, account change, privacy action,
  payment action, or other external operation was completed unless the supplied sources
  explicitly confirm that it already happened.
- Do not invent policies, timelines, product capabilities, or commitments.
- source_ids must include only supplied source IDs actually used in the draft.
- Set requires_account_action=true when resolving the ticket requires an external system
  or human to change an account, order, payment, subscription, or privacy state.
- Set unsupported_action_claimed=true if the draft contains a claim that an external
  action happened without evidence in the supplied context. Normally this should be false.
- Keep the response concise, helpful, and suitable for human review or sending.
- Do not expose hidden chain-of-thought.
"""


class DraftingService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def draft(
        self,
        ticket: SupportTicketIn,
        classification: TicketClassification,
        sources: list[RetrievedSource],
    ) -> DraftResponse:
        source_text = "\n\n".join(
            f"[{source.source_id}] {source.title}\n{source.excerpt}"
            for source in sources
        )
        user_prompt = (
            f"Ticket ID: {ticket.ticket_id}\n"
            f"Customer message: {ticket.customer_message}\n"
            f"Category: {classification.category.value}\n"
            f"Intent: {classification.intent_summary}\n\n"
            f"Knowledge sources:\n{source_text or 'No relevant sources found.'}"
        )
        draft = await self.provider.generate_structured(
            system_prompt=DRAFT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=DraftResponse,
        )

        valid_source_ids = {source.source_id for source in sources}
        unknown_source_ids = set(draft.source_ids) - valid_source_ids
        if unknown_source_ids:
            raise ValueError(
                "Draft cited unknown knowledge sources: "
                + ", ".join(sorted(unknown_source_ids))
            )
        return draft
