# RelayDesk n8n Orchestration

RelayDesk uses n8n as the orchestration layer around a Python/FastAPI decision service. The AI and business rules stay in code; n8n owns event intake, retries, branching, and workflow continuation.

## Why two workflows?

RelayDesk intentionally does **not** keep a single n8n execution sleeping while a human decides what to do. Human review may take minutes, hours, or longer, and an n8n restart should not erase the pending decision.

Instead:

1. `relaydesk-intake.json` receives a support ticket and calls `POST /api/v1/process`.
2. RelayDesk persists the full workflow state in SQLite.
3. Auto-eligible tickets return immediately as completed.
4. Human-review tickets return `202` with the persisted `workflow_id` and review context.
5. The later review dashboard submits a human decision to `relaydesk-review-continuation.json`.
6. That workflow calls `POST /api/v1/workflows/{workflow_id}/review` and resumes the stored state.

This makes human-in-the-loop processing durable and restart-safe.

## Required n8n environment variable

Set:

```text
RELAYDESK_API_URL=http://host.docker.internal:8000
```

Use the URL from which your n8n instance can reach FastAPI. If both services run in the same Docker network, use the FastAPI service name instead of `host.docker.internal`.

No LLM credentials are stored in n8n. Provider configuration remains in RelayDesk's backend environment.

## Workflow 1 — Support Intake

Webhook:

```text
POST /webhook/relaydesk/support/intake
```

Expected body matches `SupportTicketIn`, for example:

```json
{
  "ticket_id": "demo-001",
  "customer_message": "Someone changed my password and I cannot log in.",
  "received_at": "2026-09-13T03:00:00Z",
  "source": "email"
}
```

Flow:

```text
Webhook
  ↓
POST FastAPI /api/v1/process
  ↓
Retry up to 3 times on request failure
  ↓
Completed?
 ├─ yes → return 200 + grounded draft
 └─ no  → return 202 + review package + workflow_id
```

The backend remains the source of truth for classification, retrieval, drafting, routing, persistence, and audit events.

## Workflow 2 — Review Continuation

Webhook:

```text
POST /webhook/relaydesk/review/continue
```

Expected body:

```json
{
  "workflow_id": "<persisted workflow id>",
  "ticket_id": "demo-001",
  "action": "edit_and_approve",
  "reviewer_id": "reviewer-001",
  "reviewed_at": "2026-09-13T03:10:00Z",
  "edited_response": "Updated response approved by the reviewer.",
  "notes": "Adjusted wording before sending."
}
```

Supported actions:

- `approve` → `completed`
- `edit_and_approve` → saves edited response, then `completed`
- `reject` → `rejected`
- `escalate` → `escalated`

The review endpoint rejects decisions for workflows that are not currently `awaiting_review`, rejects mismatched ticket IDs, and requires `edited_response` for `edit_and_approve`.

## Importing into n8n

Import both JSON files through n8n's workflow import UI. Keep them inactive until `RELAYDESK_API_URL` is configured and the FastAPI service is reachable. Then activate both webhook workflows.

## Design responsibilities

| Layer | Responsibility |
| --- | --- |
| n8n | webhooks, retries, branching, orchestration, continuation |
| FastAPI | validation, application API, persisted workflow transitions |
| LLM provider | structured classification and grounded drafting |
| deterministic policy | confidence/risk routing and safety overrides |
| SQLite | workflow state, audit history, metrics foundation |
| future dashboard | review/edit/approve/reject/escalate UI |

This split is deliberate: n8n coordinates the process, but correctness and safety rules remain testable application code.
