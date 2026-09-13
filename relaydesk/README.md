# RelayDesk

**AI Customer Support Triage & Resolution System**

Status: **Project 01 — Classification + routing backend implemented**

RelayDesk is the first flagship system in the AI Automation Specialist portfolio. It turns incoming support requests into validated structured data, retrieves relevant knowledge, drafts responses, routes by confidence/risk, and sends uncertain cases to a real human review experience.

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

## Target Architecture

```text
Incoming Request
      ↓
Webhook / API
      ↓
Input Validation
      ↓
AI Classification → Structured Schema
      ↓
Knowledge Retrieval
      ↓
Draft Response
      ↓
Confidence + Risk Policy
   ↙              ↘
Auto Route       Human Review
   ↘              ↙
      Final Action
           ↓
      Audit + Metrics
```

## Implemented Backend Core

RelayDesk now includes:

- explicit product and automation requirements
- 32 labeled synthetic benchmark tickets
- Pydantic domain schemas
- vendor-neutral `LLMProvider` interface
- real Ollama `/api/chat` structured-output adapter
- provider factory
- classification prompt + classification service
- deterministic confidence/risk routing policy
- FastAPI `/api/v1/classify` endpoint
- FastAPI `/health` endpoint
- normalized provider failure handling
- tests for classification contracts, routing, validation, policy override, and provider outage behavior
- GitHub Actions CI with Ruff + pytest
- zero-cost Ollama-first configuration
- benchmark/evaluation plan and quality targets

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
│       ├── prompts.py
│       ├── schemas.py
│       ├── providers/
│       │   ├── base.py
│       │   ├── factory.py
│       │   └── ollama.py
│       └── services/
│           ├── classification.py
│           └── routing.py
├── tests/
│   ├── test_api.py
│   ├── test_classification_service.py
│   └── test_routing.py
├── data/
│   └── support_tickets.jsonl
└── docs/
    ├── architecture.md
    ├── evaluation-plan.md
    └── requirements.md
```

## Routing Policy

The model may recommend a route, but deterministic application logic owns the final route.

```text
high-risk flag present   → human review
confidence >= 0.90       → auto eligible
confidence 0.70–0.89     → human verification
confidence < 0.70        → manual processing
```

This means even a 0.99-confidence model response cannot auto-process a ticket carrying an account-security, payment-dispute, legal, privacy, chargeback, data-loss, or safety risk flag.

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

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/classify \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id":"demo-001",
    "customer_message":"Someone changed my password and I cannot log in.",
    "received_at":"2026-09-13T02:00:00Z",
    "source":"email"
  }'
```

The response contains both the model classification and RelayDesk's deterministic routing decision.

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
- [x] First FastAPI endpoint
- [x] Core automated tests
- [x] Backend CI foundation
- [ ] n8n workflow
- [ ] Retrieval layer
- [ ] Human-review dashboard
- [ ] Evaluation harness
- [ ] Persistence + audit events
- [ ] Expanded failure handling and observability
- [ ] Deployment
- [ ] Final case study + demo video

## Next Implementation Step

Build the retrieval + drafting layer so RelayDesk can move from **classify and route** to **classify → retrieve evidence → draft a grounded reply → route** before n8n orchestrates the complete workflow.
