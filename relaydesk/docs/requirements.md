# RelayDesk Requirements

## Purpose

RelayDesk is a portfolio-grade AI customer support triage and resolution system that demonstrates how probabilistic AI can be embedded inside a reliable business workflow without allowing the model to control every downstream action.

The system must be understandable to a hiring manager, inspectable by an engineer, and explainable by Brianna Dickenson in an interview.

## Business Scenario

RelayDesk models a fictional SaaS company with a small support team handling customer questions through a shared support inbox.

The team currently performs eight routine steps for each request:

1. Read the incoming message.
2. Identify the request category.
3. Determine urgency and priority.
4. Search internal support documentation.
5. Draft a reply.
6. Decide whether the request is safe for automation.
7. Route, assign, resolve, or escalate the ticket.
8. Record the final action for reporting.

RelayDesk automates the repeatable portions while reserving uncertain, sensitive, or risky cases for human review.

## Primary User Roles

### Support Agent

- Reviews tickets routed to the human-review queue.
- Sees original customer text, AI classification, retrieved context, draft response, confidence, and routing recommendation.
- Can approve, edit and approve, reject, or escalate.

### Support Manager

- Reviews operational metrics.
- Examines automation rate, classification accuracy, human override rate, latency, failures, and category distribution.
- Audits why a ticket was automated or routed to a person.

### System Administrator

- Configures model provider, confidence thresholds, and integration settings.
- Can run the system locally with Ollama or configure a supported cloud provider.

## Functional Requirements

### 1. Intake

The system must accept a support request containing at minimum:

- unique ticket ID
- customer message
- received timestamp

Optional fields may include:

- customer ID
- customer name
- account tier
- prior ticket count
- source/channel

### 2. Input Validation

Before model execution, RelayDesk must:

- reject empty messages
- enforce maximum input length
- normalize whitespace
- preserve the unmodified original message for audit purposes
- distinguish malformed payloads from model failures

### 3. AI Classification

The classification stage must return schema-validated structured data rather than free-form prose.

Required outputs:

- category
- intent summary
- priority
- sentiment
- confidence
- risk flags
- recommended route
- rationale summary suitable for reviewer inspection

### 4. Supported Categories

Initial categories:

- account_access
- billing
- cancellation
- refund
- technical_issue
- product_question
- feature_request
- shipping_or_delivery
- complaint
- other

The `other` category exists so the model is not forced to fabricate a fit.

### 5. Priority Levels

- low
- normal
- high
- urgent

Urgency must not be based only on emotional language. Deterministic policies may override model priority when explicit risk conditions are present.

### 6. Risk Flags

Initial risk flags:

- account_security
- payment_dispute
- legal_threat
- self_harm_or_safety
- abusive_content
- privacy_request
- chargeback
- data_loss
- none

A ticket may contain multiple risk flags.

### 7. Retrieval

RelayDesk must retrieve relevant knowledge-base material using the classified category and customer message.

Retrieved evidence must be kept separate from model-generated text so the reviewer can see what information the draft was based on.

### 8. Draft Generation

The response-drafting stage must:

- use retrieved support context when available
- avoid claiming actions that have not actually occurred
- avoid fabricating refunds, account changes, credits, or technical fixes
- clearly defer to a human when policy or account-specific action is required

### 9. Routing Policy

Initial routing thresholds:

- confidence >= 0.90 AND no risk flags: eligible for automatic processing
- confidence 0.70–0.89: human verification
- confidence < 0.70: manual processing
- any high-risk flag: human review regardless of confidence

These thresholds are configurable and intentionally separated from the model prompt.

### 10. Human Review

A reviewer must be able to:

- approve
- edit and approve
- reject
- escalate

Every decision must create an audit event recording:

- reviewer action
- timestamp
- previous recommendation
- final route
- whether the AI recommendation was overridden

### 11. Failure Handling

RelayDesk must handle at minimum:

- unavailable LLM provider
- timeout
- malformed model output
- schema validation failure
- retrieval failure
- empty retrieval result
- downstream action failure
- duplicate ticket submission

Failures must be classified and recorded rather than silently swallowed.

### 12. Provider Portability

The application must expose a common provider interface so the orchestration and business logic do not depend directly on a single AI vendor.

Target providers:

- Ollama/local models — zero-cost primary development option
- OpenAI-compatible API
- Anthropic
- Gemini

Cloud providers are optional at runtime and must never be required for the zero-cost path.

## Non-Functional Requirements

### Reliability

- Structured outputs must be validated before downstream use.
- Workflow steps that can be retried safely should be idempotent.
- Duplicate incoming ticket IDs must not create duplicate final actions.

### Auditability

The system must preserve:

- original request
- normalized request
- model/provider used
- model output before validation where safe to retain
- validated structured output
- retrieved source identifiers
- routing decision
- human decision if present
- final action
- timestamps and latency measurements

### Security

- secrets must come from environment variables
- `.env` files must not be committed
- no real customer personal information will be used in the portfolio dataset
- synthetic test data must be clearly labeled as synthetic

### Accessibility

The later review dashboard must support keyboard navigation, visible focus, semantic controls, clear status text, and responsive layouts.

### Cost

The complete development and demo path must have a no-cost configuration. Ollama/local inference is the guaranteed zero-cost model option.

## Acceptance Criteria for Project 01

RelayDesk is considered portfolio-complete only when:

1. A support ticket can enter through the API/workflow.
2. Classification returns validated structured data.
3. Retrieval provides inspectable support context.
4. A response draft is produced without unsupported actions.
5. Deterministic confidence/risk routing is applied.
6. Human-review cases can be approved, edited, rejected, or escalated.
7. Audit events are recorded.
8. The evaluation harness runs against the labeled synthetic dataset.
9. Failure scenarios are tested.
10. Dashboard metrics are generated from actual benchmark runs.
11. The project can run with Ollama without paid services.
12. The portfolio case study reports benchmark results honestly and distinguishes them from production outcomes.
