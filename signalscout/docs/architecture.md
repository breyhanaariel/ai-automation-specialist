# SignalScout Architecture

## Design Principle

AI assists with interpretation and generation, but deterministic application policy owns the final score, qualification band, CRM action eligibility, and whether human review is required.

## High-Level Flow

```text
Website / CSV / Webhook
          ↓
        n8n
          ↓
   FastAPI Intake API
          ↓
Validation + Normalization
          ↓
Duplicate Detection
          ↓
Enrichment Adapter
          ↓
AI Intent / Role Analysis
          ↓
Deterministic Weighted Score
          ↓
Business Rule Overrides
    ┌────────┴────────┐
    ↓                 ↓
Ready for CRM      Human Review
    ↓                 ↓
CRM Adapter      Review Dashboard
    ↓                 ↓
Follow-up Task   Approve/Edit/Nurture/
+ Outreach Draft Disqualify/Duplicate
    └────────┬────────┘
             ↓
        Audit + Metrics
             ↓
      Evaluation Harness
```

## Application Boundaries

### n8n
Responsible for:
- receiving external webhooks
- CSV/import orchestration
- calling SignalScout APIs
- future third-party CRM/enrichment connectors
- integration retries where appropriate

Not responsible for:
- score calculation
- qualification thresholds
- validation schemas
- final policy decisions

### FastAPI
Responsible for:
- typed API contracts
- input validation and normalization
- idempotency
- enrichment abstraction
- AI provider abstraction
- score calculation
- qualification and override policy
- workflow state
- CRM adapter contract
- review decisions
- audit and metrics

### Dashboard
Responsible for:
- showing the evidence behind a lead score
- editing scoring weights
- reviewing ambiguous or strategic leads
- editing and approving outreach drafts
- showing audit history and operational metrics

The browser talks directly to FastAPI. n8n is the external orchestration path. Both converge on the same backend business logic.

## Core Domain Entities

Planned entities:
- LeadSubmission
- NormalizedLead
- EnrichmentProfile
- IntentAnalysis
- ScoreComponent
- LeadScore
- RoutingDecision
- CRMRecord
- OutreachDraft
- HumanReviewDecision
- WorkflowState
- AuditEvent
- ScoringConfiguration

## Lead Scoring

The scoring service accepts validated inputs and a versioned ScoringConfiguration.

Default weights:
```text
company_fit            30
role_fit               20
intent                  25
data_quality            10
geography               10
source_quality           5
--------------------------
total                  100
```

The scorer must return:
- total score
- component scores
- applied weights
- concise explanation for each component
- scoring configuration version

The scorer must be deterministic for identical normalized inputs and configuration.

## Qualification Policy

Default score bands:
```text
80-100  sales_qualified
60-79   review
40-59   nurture
0-39    disqualify
```

Hard overrides execute after scoring.

Examples:
- spam -> disqualify
- strategic account -> human_review
- exact duplicate -> duplicate_review
- unsupported geography -> nurture/disqualify
- enrichment uncertainty on high-value account -> human_review

The final RoutingDecision stores both the score recommendation and the policy-adjusted route.

## Provider Abstraction

```python
class AIProvider(Protocol):
    name: str
    model: str

    async def generate_structured(...): ...
```

Initial implementations:
- OllamaProvider: real local inference
- DemoProvider: deterministic zero-cost public demonstration, explicitly not an LLM

Reserved adapters:
- OpenAI
- Anthropic
- Gemini

## Enrichment Abstraction

```python
class EnrichmentProvider(Protocol):
    name: str
    async def enrich(lead: NormalizedLead) -> EnrichmentProfile: ...
```

Initial implementation:
- DemoEnrichmentProvider backed by deterministic synthetic fixture data

Future adapters can wrap enrichment APIs without changing scoring logic.

## CRM Abstraction

```python
class CRMProvider(Protocol):
    async def upsert_lead(...): ...
    async def create_follow_up_task(...): ...
```

Initial implementation:
- DemoCRMProvider persisted locally/Neon

A future HubSpot adapter maps the same domain operations to API calls.

## Persistence

Local:
```text
sqlite:///./signalscout.db
```

Public:
```text
postgresql://... Neon ...
```

Planned tables:
- workflows
- leads
- enrichment_profiles
- scoring_configs
- audit_events
- idempotency_keys
- crm_records

JSONB may be used for versioned snapshots while queryable routing/status fields remain first-class columns.

## Workflow State

Planned states:
- received
- validated
- enriched
- analyzed
- scored
- awaiting_review
- ready_for_crm
- crm_synced
- outreach_pending_approval
- completed
- nurture
- disqualified
- duplicate_review
- escalated
- failed

No state named `completed` may be used until the workflow's configured final action has actually succeeded.

## Human-in-the-Loop

Review cases expose:
- submitted lead data
- normalized values
- enrichment evidence
- duplicate evidence
- AI analysis
- score component breakdown
- score recommendation
- policy override rationale
- CRM action preview
- outreach draft

Actions:
- approve
- edit_and_approve
- nurture
- disqualify
- mark_duplicate
- escalate_strategic

## Observability

Each workflow records:
- workflow ID
- lead ID
- correlation ID
- provider/model names
- enrichment provider
- CRM provider
- configuration version
- stage latencies
- retry counts
- structured error code/message
- policy overrides
- human override events

## Deployment

Target public architecture:
```text
Vercel FastAPI + static dashboard
            ↓
        Neon Postgres
```

Public demo uses deterministic AI/enrichment/CRM adapters and no paid keys. Local development can use Ollama for genuine model inference.
