# RelayDesk Backend Architecture

## Design Principle

RelayDesk uses AI as one decision-support layer inside a larger deterministic workflow. Model output is never trusted directly by downstream actions.

## System Boundaries

```text
Client / n8n
    ↓
FastAPI application
    ↓
Request validation
    ↓
Classification service
    ↓
LLM provider abstraction
    ↓
Structured output validation
    ↓
Retrieval service
    ↓
Draft service
    ↓
Routing policy
 ┌───────────────┐
 │               │
Auto-eligible   Human review
 │               │
 └───────┬───────┘
         ↓
Action service
         ↓
Audit + metrics
```

## Planned Application Layout

```text
relaydesk/
├── backend/
│   └── app/
│       ├── config.py
│       ├── schemas.py
│       ├── providers/
│       │   ├── base.py
│       │   ├── factory.py
│       │   └── README.md
│       ├── services/
│       │   ├── classification.py
│       │   ├── retrieval.py
│       │   ├── drafting.py
│       │   ├── routing.py
│       │   └── audit.py
│       └── api/
│           └── routes.py
├── data/
├── docs/
├── evals/
├── prompts/
├── tests/
└── workflows/
```

## Responsibility Boundaries

### API Layer

Responsible for transport concerns only:

- receive request
- validate top-level payload
- return response/status
- map domain errors to HTTP responses

It should not contain model prompts or business routing rules.

### Classification Service

Responsible for:

- preparing the classification prompt/input
- invoking the configured provider
- validating provider output against `TicketClassification`
- returning typed application data

### Provider Layer

Responsible for vendor-specific model calls.

The rest of the application should depend only on the abstract interface.

Expected provider method:

```python
async def generate_structured(
    *,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
) -> T:
    ...
```

### Retrieval Service

Responsible for:

- selecting/searching knowledge-base content
- returning source IDs and excerpts
- returning an empty result cleanly if nothing relevant is found

The retrieval layer must never fabricate sources.

### Drafting Service

Responsible for:

- constructing a reply from the customer request plus retrieved context
- producing a draft only
- never recording external actions as completed unless confirmed by another service

### Routing Policy

Responsible for deterministic decisions after classification.

Example policy:

```text
if any high-risk flag:
    HUMAN_REVIEW
elif confidence >= 0.90:
    AUTO_ELIGIBLE
elif confidence >= 0.70:
    HUMAN_VERIFY
else:
    MANUAL
```

The model may recommend a route, but the policy service owns the final system route.

### Human Review Service

Responsible for:

- pending review state
- reviewer decision
- edited draft if applicable
- override detection
- workflow resume state

### Audit Service

Responsible for append-only business events such as:

- ticket_received
- classification_completed
- classification_failed
- retrieval_completed
- draft_generated
- routing_decided
- human_review_requested
- human_review_completed
- action_completed
- workflow_failed

## Provider Abstraction

The provider abstraction exists for three reasons:

1. Keep the zero-cost Ollama path first-class.
2. Demonstrate vendor portability.
3. Prevent provider SDK objects from leaking into application logic.

Provider implementations must normalize failures into application-level exceptions such as:

- ProviderUnavailableError
- ProviderTimeoutError
- ProviderOutputError

## Configuration

Initial environment contract:

```text
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:7b
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
CLASSIFICATION_AUTO_THRESHOLD=0.90
CLASSIFICATION_REVIEW_THRESHOLD=0.70
```

Provider-specific secrets are optional unless that provider is selected.

## Persistence Strategy

Development can begin with SQLite for a zero-cost local path. The persistence contract should remain simple enough to migrate to PostgreSQL/Supabase later without changing the domain models.

Initial persisted entities:

- Ticket
- TicketClassification
- RetrievedSource
- DraftResponse
- RoutingDecision
- HumanReview
- AuditEvent

## Idempotency

The incoming `ticket_id` is the first idempotency key.

A duplicate submission should return the existing workflow state instead of triggering classification, drafting, and final actions again.

## Observability

Every workflow execution should eventually capture:

- workflow ID
- ticket ID
- provider
- model
- started_at
- completed_at
- stage latencies
- final route
- failure code if any
- human override boolean

These fields power both debugging and portfolio metrics.

## What n8n Will Own Later

n8n will coordinate external workflow steps, event triggers, and integrations.

FastAPI/Python will own typed business logic, model-provider abstraction, validation, evaluation, and reusable domain services.

That separation prevents RelayDesk from becoming a no-code-only demo while still proving practical orchestration skills.
