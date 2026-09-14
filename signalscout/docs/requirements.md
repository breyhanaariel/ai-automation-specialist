# SignalScout Requirements

## Purpose

SignalScout is a portfolio-grade AI lead qualification and CRM automation system for a fictional B2B services company. It demonstrates how lead intake, enrichment, explainable scoring, CRM synchronization, personalized outreach drafting, and human approval can be combined into a reliable business workflow.

The system must be understandable to a hiring manager, technically inspectable by an engineer, and explainable by Brianna Dickenson in an interview.

## Business Scenario

A small B2B services team receives leads from website forms, manual/CSV imports, and partner/API webhooks. Today the team manually validates contact data, researches the company, checks fit, scores intent, looks for duplicates, chooses an owner, updates the CRM, creates follow-up work, and drafts outreach.

SignalScout automates repeatable steps while keeping ambiguous, strategic, duplicate, or risky decisions under human control.

## Primary User Roles

### Sales Representative
- reviews assigned leads and outreach drafts
- approves or edits personalized outreach
- can move a lead to nurture or disqualify it

### Sales Manager
- reviews score distributions, qualification rate, overrides, CRM sync health, and pipeline throughput
- configures scoring weights and business-rule thresholds
- audits why a lead received a score and route

### System Administrator
- configures model provider, CRM adapter, enrichment providers, database connection, and integration secrets
- can run locally with Ollama and deterministic demo adapters

## Functional Requirements

### 1. Intake
SignalScout must accept leads from:
- website form
- CSV/manual import
- webhook/API

Minimum lead fields:
- lead ID
- full name
- email
- company name
- source
- received timestamp

Optional fields:
- job title
- company domain
- phone
- country/region
- message or inquiry
- employee count
- industry
- annual revenue band

### 2. Validation and Normalization
Before enrichment or AI execution, SignalScout must:
- reject empty required fields
- normalize whitespace and casing where safe
- validate email shape
- normalize job titles into role families
- normalize domains
- preserve original submitted values for audit
- distinguish malformed input from downstream failures

### 3. Duplicate Detection
The system must detect probable duplicates using deterministic identifiers first:
- normalized email
- normalized domain + name
- CRM external ID when available

Probable duplicates must never silently create a second CRM record. They route to merge/review unless a deterministic exact match can safely update an existing lead.

### 4. Enrichment
Initial enrichment outputs:
- company/domain resolution
- industry
- company size band
- location
- normalized role/title
- business email quality
- duplicate status
- optional short company summary

The public demo must work with deterministic synthetic/mock enrichment. Real enrichment adapters may be added without changing business logic.

### 5. AI-Assisted Analysis
AI may assist with:
- inquiry/intent summary
- buying-intent classification
- role relevance
- company-summary normalization
- outreach-draft personalization

AI outputs must use schema-validated structured data. AI must not directly determine final CRM actions.

### 6. Explainable Lead Scoring
Final score range: 0-100.

Default weighted dimensions:
- company fit: 30
- role fit: 20
- intent: 25
- data quality: 10
- geography/serviceability: 10
- engagement/source quality: 5

Weights must be configurable from the dashboard and validated to total 100.

Each score must preserve a component-by-component explanation.

### 7. Qualification Bands
Default bands:
- 80-100: sales_qualified
- 60-79: review
- 40-59: nurture
- 0-39: disqualify

Bands are deterministic business rules, not model instructions.

### 8. Override Rules
Initial hard overrides:
- invalid/spam lead -> disqualify
- exact duplicate -> merge/update or review
- strategic account -> human review
- unsupported geography -> disqualify or nurture according to policy
- low-confidence enrichment on a high-value lead -> human review

Overrides must record whether the score-based recommendation was changed.

### 9. CRM Automation
For an approved sales-qualified lead, SignalScout must support a CRM adapter capable of:
- create or update contact/company records
- assign an owner
- create a follow-up task
- record qualification score and explanation
- store source and enrichment metadata

The zero-cost public path must use a mock/local CRM adapter. The architecture must remain portable to HubSpot-style APIs.

### 10. Outreach Drafting
SignalScout may generate a personalized outreach draft using validated lead/enrichment context.

It must:
- avoid fabricating company facts
- avoid unsupported promises
- identify the context used
- never send email automatically in the portfolio implementation

Every outbound message requires explicit human approval.

### 11. Human Review
The sales review dashboard must allow:
- approve
- edit and approve
- nurture
- disqualify
- mark/merge duplicate
- escalate strategic account

Every decision creates an audit event.

### 12. Dashboard
Required sections:
- Overview
- Lead Queue
- Qualified Leads
- Review Queue
- Scoring Rules
- Activity / Audit
- Metrics

The product visual identity is soft teal + lavender and remains recognizably part of the Brianna Dickenson portfolio family.

### 13. Metrics
Track at minimum:
- total leads processed
- sales-qualified rate
- review rate
- nurture rate
- disqualification rate
- duplicate rate
- enrichment success rate
- CRM sync success/failure
- average processing latency
- human override rate
- score distribution
- projected time saved from the synthetic benchmark

Projected impact must be labeled as simulated, not client results.

### 14. Evaluation Dataset
Create 40-50 labeled synthetic leads covering:
- strong fit
- weak fit
- spam
- duplicates
- unsupported geography
- ambiguous intent
- strategic accounts
- malformed/partial enrichment

Evaluation must measure deterministic scoring/routing correctness separately from model-quality metrics.

### 15. Provider Portability
Initial providers:
- Ollama/local model
- deterministic public demo provider

The common interface must allow future OpenAI, Anthropic, and Gemini adapters without changing workflow logic.

### 16. Persistence
- SQLite for local zero-config development
- PostgreSQL/Neon for durable public deployment
- SignalScout gets its own Neon project/database

### 17. Orchestration
n8n + FastAPI use a two-layer approach:
- n8n handles external intake and integration orchestration
- FastAPI owns typed validation, enrichment contracts, scoring policy, routing, persistence, and review state

### 18. Reliability
SignalScout must support:
- idempotent intake
- retries for retry-safe provider/integration failures
- structured error codes
- audit trail
- correlation IDs
- stage latency measurements
- explicit failure states

### 19. Security
- secrets from environment variables only
- no committed credentials
- synthetic portfolio data only
- public demo performs no real outbound email
- CRM writes in the public demo are sandbox/mock only

## Acceptance Criteria

SignalScout is portfolio-complete only when:
1. all three intake modes are supported
2. validation, enrichment, duplicate detection, scoring, and routing are implemented
3. score explanations are inspectable
4. scoring weights can be changed safely
5. CRM create/update behavior works through an adapter
6. outreach drafts require human approval
7. review actions persist and continue the workflow
8. audit and metrics APIs work
9. the benchmark dataset and evaluation harness run reproducibly
10. failure and idempotency paths are tested
11. local Ollama and zero-cost demo modes both work
12. Neon-backed public persistence is available
13. documentation clearly labels synthetic benchmark results and projected impact
