# SignalScout Evaluation Plan

## Goal

Measure deterministic scoring/routing quality separately from probabilistic AI quality so portfolio claims remain honest and reproducible.

## Synthetic Benchmark

Target: 48 labeled leads.

Coverage should include:
- strong-fit buyers
- weak-fit leads
- spam
- exact and probable duplicates
- unsupported geography
- ambiguous intent
- strategic accounts
- incomplete enrichment
- poor email quality
- high-value accounts with low-confidence enrichment

Each benchmark case should define expected labels for deterministic outcomes and, where applicable, expected AI classification ranges.

## Deterministic Metrics

- qualification-band accuracy
- hard-override accuracy
- duplicate-routing accuracy
- unsupported-geography routing accuracy
- strategic-account review recall
- scoring reproducibility rate
- configuration validation success rate
- CRM action eligibility accuracy

## AI/Enrichment Metrics

When using an actual model/provider:
- intent classification accuracy
- role relevance accuracy
- schema success rate
- enrichment completion rate
- hallucinated company-fact count
- grounded outreach rate

## Operational Metrics

- workflow failure rate
- provider retry count
- CRM sync success rate
- average end-to-end latency
- average validation/enrichment/analysis/scoring/CRM latency
- human override rate
- idempotent replay count

## Safety / Business-Control Checks

The evaluation must fail if any of the following occurs:
- spam is marked sales-qualified
- an exact duplicate silently creates a second CRM record
- a strategic account bypasses required review
- an unsupported-geography lead is routed as directly sales-qualified when policy forbids it
- an outreach message is marked sent without a human approval action
- an ungrounded company fact is introduced into outreach

## Initial Engineering Targets

Targets are not claims until measured:
- qualification-band accuracy >= 95%
- hard-override accuracy = 100%
- duplicate-routing accuracy = 100%
- strategic-account review recall = 100%
- schema success rate >= 98%
- workflow failure rate < 2%
- zero unauthorized outbound sends

## Reporting Language

Use:
**Benchmark result from a labeled synthetic dataset**

Projected business impact may estimate time saved from the simulated manual workflow, but must be labeled:
**Projected impact based on synthetic benchmark assumptions**

Do not present synthetic results as production-client outcomes.
