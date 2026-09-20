# Security and Safety Controls

SignalScout treats model/provider output as advisory. Deterministic policy owns routing. Outbound email is never sent automatically.

- Secrets are environment variables and never committed.
- Pydantic validates inbound lead data.
- Database operations use parameterized queries.
- Duplicate and strategic-account rules force review.
- Unsupported geography is routed away from direct qualification.
- Every persisted workflow creates an audit event.
- Public demo data is synthetic; no production customer data is included.
- The deterministic demo provider is explicitly not represented as an LLM.
