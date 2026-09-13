# RelayDesk Deployment

## Goal

Deploy a public portfolio demo without requiring a paid GPU or pretending deterministic demo behavior is LLM inference.

## Runtime Modes

### Local development

```text
LLM_PROVIDER=ollama
DATABASE_URL=sqlite:///./relaydesk.db
```

This is the real local LLM path and keeps workflow state in local SQLite.

### Public portfolio demo

The Vercel configuration uses:

```text
ENVIRONMENT=public-demo
LLM_PROVIDER=demo
LLM_MODEL=deterministic-demo-v1
DATABASE_URL=sqlite:////tmp/relaydesk.db
LLM_MAX_RETRIES=0
```

The `demo` provider is intentionally deterministic and explicitly documented as **not an LLM**. It exists so hiring managers can exercise the workflow and review interface without a paid API key.

## Vercel

Project root directory: `relaydesk`

The repository contains:

- `app.py` — Vercel FastAPI entrypoint
- `vercel.json` — function/runtime configuration
- `dashboard/` — review console assets bundled with the function
- `data/` — local knowledge base bundled with the function

## Persistence Limitation

Vercel function local storage is ephemeral. `/tmp/relaydesk.db` is sufficient for a smoke-test demo but is **not durable storage** and must not be described as production persistence.

Before the public demo is considered fully deployed, replace the public `DATABASE_URL` with a free external datastore or add a serverless repository adapter for a durable Vercel-compatible data service.

The local implementation remains SQLite-first and fully persistent on the developer machine.

## Security

- No provider keys are committed to the repository.
- Public demo mode requires no API key.
- Future cloud-provider keys must be Vercel environment variables/secrets.
- Real customer data must never be placed in the synthetic portfolio demo.

## Verification Checklist

- CI: Ruff passes
- CI: pytest passes
- `/health` reports `public-demo` and `demo` provider after deployment
- `/review/` loads dashboard assets
- `/api/v1/process` accepts a synthetic ticket
- high-risk demo input routes to human review
- review queue renders the workflow
- reviewer decision endpoint works within the same live instance
- persistent datastore configured before claiming durable public workflow state
