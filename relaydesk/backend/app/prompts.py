from app.schemas import SupportTicketIn


CLASSIFICATION_SYSTEM_PROMPT = """You are RelayDesk's support-triage classifier.
Return only data that matches the provided schema.

Rules:
- Classify the customer's primary intent, not incidental wording.
- Confidence is your confidence in the classification fields, from 0.0 to 1.0.
- Never use confidence to hide uncertainty; lower it when the request is ambiguous.
- Flag account security, payment disputes, legal threats, privacy requests, chargebacks,
  data loss, or safety concerns whenever present.
- Use risk_flags=[\"none\"] only when no material risk flag applies.
- recommended_route is advisory only. Application policy makes the final routing decision.
- Keep rationale_summary short and operational. Do not expose hidden chain-of-thought.
"""


def build_classification_prompt(ticket: SupportTicketIn) -> str:
    metadata = {
        "ticket_id": ticket.ticket_id,
        "customer_id": ticket.customer_id,
        "customer_name": ticket.customer_name,
        "account_tier": ticket.account_tier,
        "prior_ticket_count": ticket.prior_ticket_count,
        "source": ticket.source,
        "received_at": ticket.received_at.isoformat(),
    }
    return (
        "Classify this support request.\n\n"
        f"Metadata: {metadata}\n\n"
        f"Customer message:\n{ticket.customer_message}"
    )
