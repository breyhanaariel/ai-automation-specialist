# RelayDesk

**AI Customer Support Triage & Resolution System**

Status: **Project 01 — Backend orchestration + persistence implemented**

RelayDesk is the first flagship system in the AI Automation Specialist portfolio. It turns incoming support requests into validated structured data, retrieves relevant knowledge, drafts grounded responses, routes by confidence/risk, persists the workflow, and sends uncertain cases through a durable human-review path.

## Business Problem

A manual support workflow often looks like:

1. Read the incoming message
2. Identify intent/category
3. Determine priority
4. Search documentation
5. Draft a response
6. Decide whether the response is safe to send
7. Assign/escalate the ticket
8. Record the action

RelayDesk automates the repetitive portions while preserving human judgment for uncertain or higher-risk cases.

## Current Architecture

```text
Incoming Request
      ↓
n8n Intake Webhook
      ↓
FastAPI /process
      ↓
Input Validation
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
                Human Dashboard
                      ↓
             n8n Review Continuation
                      ↓
           Approve / Edit / Reject / Escalate
                      ↓
                 Audit + Metrics
```

## Implemented Core

RelayDesk now includes:

- explicit product and automation requirements
- 32 labeled synthetic benchmark tickets
- Pydantic domain schemas
- vendor-neutral `LLMProvider` interface
- real Ollama `/api/chat` structured-output adapter
- provider factory
- classification prompt + service
- deterministic confidence/risk routing policy
- local knowledge base + lexical retrieval
- grounded response drafting + citation validation
- unsupported-action safety override
- SQLite workflow-state persistence
- ordered audit events
- workflow metrics foundation
- durable human-review decision endpoint
- n8n support-intake workflow
- n8n review-continuation workflow
- retry behavior around backend HTTP calls
- FastAPI workflow/audit/metrics endpoints
- GitHub Actions CI with Ruff + pytest
- zero-cost Ollama-first configuration

## Repository Structure

```text
relaydesk/
├── .env.example
├── README.md
├── pyproject.toml
├── backend/
│   └── app/
│       ├── api.py
│       ├── config.py
│       ├── main.py
│       ├── persistence.py
│       ├── prompts.py
│       ├── schemas.py
│       ├── providers/
│       └── services/
├── data/
│   ├── knowledge_base.json
│   └── support_tickets.jsonl
├── docs/
├── n8n/
│   ├── README.md
│   ├── relaydesk-intake.json
│   └── relaydesk-review-continuation.json
└── tests/
```

## Routing Policy

The model may recommend a route, but deterministic application logic owns the final route.

```text
high-risk flag present   → human review
confidence >= 0.90       → auto eligible
confidence 0.70–0.89     → human verification
confidence < 0.70        → manual processing
```

A second gate checks the drafted reply. If the draft claims an unsupported external action, RelayDesk overrides the normal route and forces human review.

## Durable Human Review

RelayDesk deliberately separates review from the original n8n execution.

A review-required ticket is saved as `awaiting_review`. The later dashboard will submit one of:

- `approve`
- `edit_and_approve`
- `reject`
- `escalate`

The review-continuation workflow then calls the persisted workflow endpoint and transitions the same workflow to `completed`, `rejected`, or `escalated`.

This avoids holding an n8n execution open for hours and makes the process restart-safe.

## Run Locally

From `relaydesk/`:

```bash
python -m venv .venv
```

Activate the environment, then install:

```bash
pip install -e ".[dev]"
```

Copy the environment template:

```bash
cp .env.example .env
```

Make sure Ollama is running and the configured model is installed, then start the API:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Open the generated API docs at `http://127.0.0.1:8000/docs`.

For n8n setup and webhook contracts, see [`n8n/README.md`](n8n/README.md).

## Provider Strategy

Current implementation:

- Ollama/local models — primary zero-cost path

Provider contract reserved for later adapters:

- OpenAI-compatible APIs
- Anthropic
- Gemini

Business logic never imports vendor SDK objects directly.

## Measurement Rules

Portfolio metrics will never be presented as real production-client results unless they actually are. Simulated/test results will be labeled as benchmark results.

Planned benchmark outputs include category accuracy, priority accuracy, risk recall, routing accuracy, automation rate, human override rate, schema success rate, processing latency, failed workflow rate, and manual-step reduction.

Initial engineering targets include >=90% category accuracy, >=95% routing accuracy, >=95% risk recall, and zero incorrectly auto-processed high-risk benchmark tickets.

## Build Sequence

- [x] Requirements
- [x] Synthetic labeled dataset
- [x] Domain schemas
- [x] Backend architecture
- [x] Provider abstraction contract
- [x] Evaluation plan
- [x] Provider factory + Ollama adapter
- [x] Classification service
- [x] Deterministic routing service
- [x] Retrieval layer
- [x] Grounded drafting layer
- [x] Persistence + audit events
- [x] Workflow metrics foundation
- [x] n8n intake workflow
- [x] n8n review continuation workflow
- [x] Backend CI foundation
- [ ] Human-review dashboard
- [ ] Evaluation harness
- [ ] Expanded failure handling and observability
- [ ] Deployment
- [ ] Final case study + demo video

## Next Implementation Step

Build the **human-review dashboard** that reads persisted `awaiting_review` workflows and lets a reviewer inspect the original message, classification, retrieved sources, draft, confidence, and route, then choose **Approve**, **Edit & Approve**, **Reject**, or **Escalate**.
