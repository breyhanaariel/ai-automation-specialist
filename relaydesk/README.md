# RelayDesk

**AI Customer Support Triage & Resolution System**

Status: **Project 01 — Reliability + observability layer implemented**

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
Auto Complete     Persist Awaiting Review
                      ↓
                Human Review Console
                      ↓
             Approve / Edit / Reject / Escalate
                      ↓
             n8n Review Continuation
                      ↓
                 Audit + Metrics
                      ↓
             Evaluation / Regression
```

## Implemented Core

- 32 labeled synthetic benchmark tickets
- Pydantic domain schemas
- vendor-neutral `LLMProvider` interface
- real Ollama structured-output adapter
- deterministic confidence/risk routing
- local knowledge base + lexical retrieval
- grounded response drafting + citation validation
- unsupported-action safety override
- SQLite workflow persistence + ordered audit events
- n8n intake + review-continuation workflows
- human-review dashboard served by FastAPI
- Approve / Edit & Approve / Reject / Escalate controls
- review queue, workflow, audit, and metrics APIs
- reproducible evaluation runner
- per-ticket benchmark diagnostics
- engineering-target pass/fail checks
- ticket-level idempotency so duplicate requests do not repeat model work
- `X-Correlation-ID` propagation through workflow state and audit events
- provider retry telemetry for timeout/unavailable failures
- structured persisted error codes and messages
- classification, retrieval, drafting, and total latency tracking
- operational metrics for failure rate, retries, replays, and stage latency
- GitHub Actions CI with Ruff + pytest

## Reliability and Observability

`POST /api/v1/process` now claims each `ticket_id` before model execution. Repeating the same ticket returns the original workflow with `idempotent_replay: true` instead of making another provider call.

Clients may send:

```text
X-Correlation-ID: your-request-id
```

The correlation ID is persisted with the workflow and copied into audit events. If none is supplied, RelayDesk uses the workflow ID.

Provider timeout and unavailable errors are retried according to:

```text
LLM_MAX_RETRIES=1
```

Each retry creates a `provider_retry` audit event. Exhausted failures remain queryable as `failed` workflows with an `error_code`, `error_message`, retry count, and total latency.

`GET /api/v1/metrics` now reports workflow counts plus failure rate, automation rate, idempotent replay count, provider retry count, and average classification/retrieval/drafting/completed latency.

## Evaluation Harness

The benchmark runner lives under `evals/` and uses `data/support_tickets.jsonl`.

Start RelayDesk with the configured model/provider available, then run:

```bash
python -m evals.runner
```

It writes machine-readable predictions and a report containing category accuracy, priority accuracy, risk recall, routing accuracy, schema success rate, workflow failure rate, automation rate, high-risk auto-processing violations, and latency summaries.

Existing predictions can be rescored without another model call:

```bash
python -m evals.runner --score-only
```

CI verifies the scoring calculations and the 32-ticket dataset contract. CI does **not** run Ollama and therefore does not claim model-quality benchmark results.

## Human Review Console

Start the API:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Then open:

```text
http://127.0.0.1:8000/review/
```

The reviewer can inspect the original request, AI classification, confidence, risk flags, routing rationale, retrieved evidence, grounded draft, and audit history before approving, editing and approving, rejecting, or escalating.

## Measurement Rules

Synthetic runs must be labeled **Benchmark result from a labeled synthetic dataset**. They must never be presented as production-client outcomes.

Initial engineering targets remain targets until a real model run produces measured results:

- category accuracy >= 90%
- routing accuracy >= 95%
- risk recall >= 95%
- schema success rate >= 98%
- workflow failure rate < 2%
- zero high-risk benchmark tickets incorrectly auto-processed

## Build Sequence

- [x] Requirements
- [x] Synthetic labeled dataset
- [x] Domain schemas
- [x] Backend architecture
- [x] Provider abstraction + Ollama adapter
- [x] Classification + deterministic routing
- [x] Retrieval + grounded drafting
- [x] Persistence + audit events
- [x] n8n orchestration
- [x] Human-review dashboard
- [x] Evaluation harness
- [x] Expanded failure handling and observability
- [x] Backend CI foundation
- [ ] Deployment
- [ ] Final case study + demo video

## Next Implementation Step

Deploy RelayDesk on a **free-first public demo architecture** while preserving local Ollama support for development. The public deployment should use a provider path that can run without a permanently hosted GPU, keep secrets out of the repo, persist demo workflow state safely, expose the review console, and clearly label any demo-provider limitations.
