# RelayDesk

**AI Customer Support Triage & Resolution System**

Status: **Project 01 — In development**

RelayDesk is the first flagship system in the AI Automation Specialist portfolio. It will turn incoming support requests into validated structured data, retrieve relevant knowledge, draft responses, route by confidence/risk, and send uncertain cases to a real human review experience.

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

RelayDesk will automate the repetitive portions while preserving human judgment for uncertain or higher-risk cases.

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

## Planned Technical Coverage

- n8n orchestration
- Python + FastAPI
- Pydantic structured outputs
- provider abstraction for Ollama / cloud LLMs
- RAG / knowledge retrieval
- confidence and policy routing
- human review: approve, edit & approve, reject, escalate
- retries and fallbacks
- audit logging
- benchmark/evaluation dataset
- measurable before/after results
- polished web dashboard
- free-first deployment strategy

## Measurement Rules

Portfolio metrics will never be presented as real production-client results unless they actually are. Simulated/test results will be labeled as benchmark or projected impact.

Planned benchmark outputs include:

- classification accuracy
- automation rate
- human override rate
- processing latency
- failed workflow rate
- manual-step reduction

## Build Sequence

1. Requirements + synthetic dataset
2. Schemas and provider abstraction
3. FastAPI service
4. n8n workflow
5. retrieval layer
6. human-review dashboard
7. evaluation harness
8. failure handling and observability
9. deployment
10. final case study + demo video
