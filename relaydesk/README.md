# RelayDesk

**AI Customer Support Triage & Resolution System**

Status: **Project 01 — Human-review + evaluation system implemented**

RelayDesk turns incoming support requests into validated structured data, retrieves relevant knowledge, drafts grounded responses, routes by confidence and risk, persists workflow state, sends uncertain cases through durable human review, and measures behavior with a reproducible synthetic benchmark.

## Current Architecture

```text
Incoming Request
      ↓
n8n Intake Webhook
      ↓
FastAPI /process
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
- GitHub Actions CI with Ruff + pytest

## Evaluation Harness

The benchmark runner lives under `evals/` and uses `data/support_tickets.jsonl`.

Start RelayDesk with the configured model/provider available, then run:

```bash
python -m evals.runner
```

It writes machine-readable predictions and a report containing:

- category accuracy
- priority accuracy
- risk recall
- routing accuracy
- schema success rate
- workflow failure rate
- automation rate
- high-risk auto-processing violations
- latency summaries

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
- [x] Backend CI foundation
- [ ] Expanded failure handling and observability
- [ ] Deployment
- [ ] Final case study + demo video

## Next Implementation Step

Expand **failure handling and observability** with stage-level latency, correlation IDs, structured failure codes, retry/fallback telemetry, duplicate/idempotency handling, and richer operational metrics before deployment.
