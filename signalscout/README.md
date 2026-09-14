# SignalScout

**Intelligent Lead Qualification & CRM Automation**

Status: **Project 02 — Foundation + specification implemented**

SignalScout is a portfolio-grade B2B lead qualification and CRM automation system. It is designed to intake leads from website forms, CSV/manual imports, and APIs; validate and enrich them; calculate an explainable 0-100 lead score; apply deterministic business-rule overrides; synchronize approved leads to a CRM adapter; draft personalized outreach; and require human approval before any outbound message.

## Locked Product Direction

- fictional B2B services company
- website, CSV/manual, and webhook/API intake
- deterministic + AI-assisted enrichment and qualification
- explainable weighted 0-100 lead scoring
- score bands: Sales Qualified / Review / Nurture / Disqualify
- override rules for spam, duplicates, strategic accounts, unsupported geography, and uncertain high-value enrichment
- CRM create/update, assignment, and follow-up task creation
- personalized outreach drafting with no automatic sending
- human-review dashboard
- editable scoring weights
- synthetic 48-lead benchmark target
- Python + FastAPI + Pydantic + Neon/Postgres + n8n
- Ollama locally + deterministic public demo provider
- separate SignalScout Neon database at deployment stage
- soft teal + lavender product identity
- synthetic results and projected impact clearly labeled

## Foundation Implemented

- product requirements: `docs/requirements.md`
- system architecture: `docs/architecture.md`
- evaluation plan: `docs/evaluation-plan.md`
- Python project/package configuration
- environment template
- FastAPI application shell
- health endpoint
- typed lead/scoring/routing schemas
- configurable scoring-weight schema
- deterministic weighted scoring engine
- score-band policy
- scoring preview API
- unit/API tests
- dedicated GitHub Actions CI

## Default Score Model

```text
company fit       30
role fit          20
intent            25
data quality      10
geography         10
source quality     5
--------------------
total            100
```

Default bands:

```text
80-100  sales_qualified
60-79   review
40-59   nurture
0-39    disqualify
```

The score recommendation is advisory to the business-policy layer. Hard rules may override it.

## Architecture

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
Follow-up Task   Human Decision
+ Outreach Draft      ↓
    └────────┬────────┘
             ↓
        Audit + Metrics
```

## Run the Foundation Locally

```bash
cd signalscout
python -m pip install -e ".[dev]"
uvicorn app.main:app --app-dir backend --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

Current endpoints:
- `GET /health`
- `GET /api/v1/scoring/defaults`
- `POST /api/v1/scoring/preview`

## Build Sequence

- [x] Product decisions
- [x] Requirements specification
- [x] Architecture specification
- [x] Evaluation plan
- [x] Backend/CI foundation
- [x] Typed lead + scoring contracts
- [x] Deterministic scoring engine
- [ ] Synthetic 48-lead benchmark dataset
- [ ] Intake + normalization
- [ ] Duplicate detection
- [ ] Enrichment provider abstraction + demo provider
- [ ] AI provider abstraction + Ollama/demo providers
- [ ] Business-rule routing overrides
- [ ] Persistence + audit + idempotency
- [ ] CRM adapter + demo CRM
- [ ] Outreach drafting
- [ ] Human-review dashboard
- [ ] Editable scoring-rule UI/API
- [ ] n8n orchestration
- [ ] Evaluation harness
- [ ] Reliability + observability
- [ ] Neon deployment persistence
- [ ] Vercel deployment
- [ ] Final case study + demo assets

## Truthfulness Rules

Synthetic evaluation must be labeled **Benchmark result from a labeled synthetic dataset**.

Any time-saved or pipeline impact estimate must be labeled **Projected impact based on synthetic benchmark assumptions**.

No simulated metric may be presented as a production-client outcome.
