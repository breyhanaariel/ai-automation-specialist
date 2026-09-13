# RelayDesk

**AI Customer Support Triage & Resolution System**

Status: **Project 01 — Foundation complete, backend implementation next**

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

## What Is Implemented Now

The project foundation now includes:

- explicit product and automation requirements
- backend architecture boundaries
- 32 labeled synthetic benchmark tickets
- Pydantic domain schemas
- vendor-neutral LLM provider interface
- normalized provider failure types
- zero-cost Ollama-first configuration
- optional cloud-provider configuration contract
- deterministic confidence-routing thresholds
- benchmark/evaluation plan and quality targets
- Python project/dependency configuration
- environment-variable template

## Current Repository Structure

```text
relaydesk/
├── .env.example
├── README.md
├── pyproject.toml
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── schemas.py
│       └── providers/
│           ├── __init__.py
│           ├── base.py
│           └── README.md
├── data/
│   └── support_tickets.jsonl
└── docs/
    ├── architecture.md
    ├── evaluation-plan.md
    └── requirements.md
```

## Routing Policy

The model may recommend a route, but deterministic application logic owns the final route.

Initial policy:

```text
risk flag present        → human review
confidence >= 0.90       → auto eligible
confidence 0.70–0.89     → human verification
confidence < 0.70        → manual processing
```

Thresholds are configurable and are not buried inside model prompts.

## Provider Strategy

RelayDesk is designed so business logic does not depend directly on one AI vendor.

Planned runtime options:

- Ollama/local models — primary zero-cost path
- OpenAI-compatible APIs — optional
- Anthropic — optional
- Gemini — optional

The application talks to a common `LLMProvider` interface instead of importing provider SDK objects throughout the codebase.

## Measurement Rules

Portfolio metrics will never be presented as real production-client results unless they actually are. Simulated/test results will be labeled as benchmark results.

Planned benchmark outputs include:

- category accuracy
- priority accuracy
- risk recall
- routing accuracy
- automation rate
- human override rate
- schema success rate
- processing latency
- failed workflow rate
- manual-step reduction

Initial engineering targets include >=90% category accuracy, >=95% routing accuracy, >=95% risk recall, and zero incorrectly auto-processed high-risk benchmark tickets.

## Build Sequence

- [x] Requirements
- [x] Synthetic labeled dataset
- [x] Domain schemas
- [x] Backend architecture
- [x] Provider abstraction contract
- [x] Evaluation plan
- [ ] Provider factory + Ollama adapter
- [ ] Classification service
- [ ] Deterministic routing service
- [ ] FastAPI endpoints
- [ ] Tests for schemas, routing, and provider failures
- [ ] n8n workflow
- [ ] Retrieval layer
- [ ] Human-review dashboard
- [ ] Evaluation harness
- [ ] Failure handling and observability
- [ ] Deployment
- [ ] Final case study + demo video

## Next Implementation Step

Build the actual Python backend core:

1. provider factory
2. Ollama structured-output adapter
3. classification service
4. deterministic routing service
5. first FastAPI endpoint
6. automated tests

No n8n or dashboard work starts until this core can classify and route benchmark tickets reliably.
