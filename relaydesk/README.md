# RelayDesk

**AI Customer Support Triage & Resolution System**

Status: **Project 01 — Application coding complete; deployment verification remains**

RelayDesk turns incoming support requests into validated structured data, retrieves relevant knowledge, drafts grounded responses, routes by confidence and risk, persists workflow state, sends uncertain cases through durable human review, measures behavior with a reproducible synthetic benchmark, and records operational telemetry for failures and retries.

## Current Architecture

```text
Incoming Request
      ↓
n8n Intake Webhook
      ↓
FastAPI /process
      ↓
Idempotency Claim + Correlation ID
      ↓
AI Classification → Structured Schema
      ↓
Knowledge Retrieval
      ↓
Grounded Draft Response
      ↓
Confidence + Risk Policy
   ↙              ↘
Ready for Action   Persist Awaiting Review
                       ↓
                 Human Review Console
                       ↓
              Approve / Edit / Reject / Escalate
                       ↓
                Ready for Action
                       ↓
              Explicit Action Completion
                       ↓
                  Audit + Metrics
                       ↓
              Evaluation / Regression
```

## Implemented Core

- 32 labeled synthetic benchmark tickets
- Pydantic domain schemas
- vendor-neutral `LLMProvider` interface
- real Ollama structured-output adapter for local inference
- deterministic zero-cost public demo provider, explicitly labeled as non-LLM
- deterministic confidence/risk routing
- local knowledge base + lexical retrieval
- grounded response drafting + citation validation
- high-risk, unsupported-action, and account-action safety overrides
- SQLite persistence for local development
- PostgreSQL/Neon persistence for hosted environments
- ticket-level idempotency so duplicate requests do not repeat model work
- ordered audit events and correlation IDs
- provider retry telemetry for timeout/unavailable failures
- structured persisted error codes and messages
- classification, retrieval, drafting, and total latency tracking
- n8n intake + review-continuation workflow definitions
- human-review dashboard served by FastAPI
- Approve / Edit & Approve / Reject / Escalate controls
- explicit `ready_for_action` state before true completion
- explicit completion endpoint for action execution handoff
- review queue, workflow, audit, and metrics APIs
- reproducible evaluation runner and per-ticket diagnostics
- GitHub Actions CI with Ruff + pytest
- Vercel-compatible FastAPI entrypoint and deployment configuration

## Persistence

RelayDesk selects persistence from `DATABASE_URL`:

- `sqlite:///...` → local SQLite repository
- `postgres://...` or `postgresql://...` → PostgreSQL repository

The hosted Neon schema contains:

- `workflows`
- `audit_events`
- `idempotency_keys`

with indexes for workflow status, ticket lookup, and audit lookup.

## Workflow State Semantics

`completed` now means the action lifecycle actually reached completion. Routing or reviewer approval alone does not falsely imply that an external action happened.

- automatic safe route → `ready_for_action`
- human-review route → `awaiting_review`
- approve/edit-and-approve → `ready_for_action`
- reject → `rejected`
- escalate → `escalated`
- explicit action completion → `completed`
- processing failure → `failed`

Any draft that requires an account-changing action is forced to human review until an authenticated external action integration exists.

## Reliability and Observability

`POST /api/v1/process` claims each `ticket_id` before provider execution. Repeating the same ticket returns the original workflow with `idempotent_replay: true` rather than making another provider call.

Clients may send `X-Correlation-ID`; otherwise RelayDesk uses the workflow ID. Provider timeout and unavailable errors retry according to `LLM_MAX_RETRIES` and emit `provider_retry` audit events.

`GET /api/v1/metrics` reports final-state counts, failure rate, auto-ready rate, idempotent replay count, provider retry count, and average processing/classification/retrieval/drafting latency.

## Evaluation Harness

The benchmark runner uses `data/support_tickets.jsonl`.

```bash
python -m evals.runner
```

Existing predictions can be rescored without another model call:

```bash
python -m evals.runner --score-only
```

CI verifies the scoring calculations and dataset contract. CI does **not** run Ollama and therefore does not claim model-quality benchmark results.

Synthetic runs must be labeled **Benchmark result from a labeled synthetic dataset** and never presented as production-client outcomes.

## Local Human Review Console

```bash
uvicorn app.main:app --app-dir backend --reload
```

Open `http://127.0.0.1:8000/review/`.

The browser review console calls the FastAPI review endpoint directly. The n8n review-continuation workflow is an alternate external orchestration entry point that converges on the same backend review logic; the documentation does not claim that the browser itself passes through n8n.

## Build Sequence

- [x] Requirements
- [x] Synthetic labeled dataset
- [x] Domain schemas
- [x] Backend architecture
- [x] Provider abstraction + Ollama adapter
- [x] Public demo provider
- [x] Classification + deterministic routing
- [x] Retrieval + grounded drafting
- [x] SQLite persistence
- [x] PostgreSQL/Neon persistence
- [x] Idempotency + audit events
- [x] n8n orchestration definitions
- [x] Human-review dashboard
- [x] Evaluation harness
- [x] Failure handling + observability
- [x] Final workflow-state semantics
- [x] Backend CI foundation
- [x] Vercel deployment code/configuration
- [ ] Live deployment secret/config verification
- [ ] Real Ollama benchmark run
- [ ] Final case-study screenshots/video

## Coding Status

**RelayDesk application coding is complete.** Remaining work is operational verification and presentation: configure the hosted `DATABASE_URL`, verify the public deployment, run the real local Ollama benchmark, and capture final case-study/demo assets.
