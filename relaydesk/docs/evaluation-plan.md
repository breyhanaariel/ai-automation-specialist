# RelayDesk Evaluation Plan

## Goal

RelayDesk must prove that the automation is useful and controlled, not merely that an LLM can return text.

All reported numbers will come from reproducible benchmark runs against labeled synthetic data unless explicitly identified otherwise.

## Benchmark Dataset

Initial labeled dataset: `data/support_tickets.jsonl`

Each record includes:

- ticket_id
- customer_message
- expected_category
- expected_priority
- expected_risk_flags
- expected_route
- notes

The dataset intentionally includes routine, ambiguous, urgent, emotionally worded, and policy-sensitive cases.

## Core Metrics

### Category Accuracy

Percentage of tickets whose predicted category matches the labeled category.

### Priority Accuracy

Percentage of tickets whose predicted priority matches the labeled priority.

### Risk Recall

Percentage of labeled risk flags correctly identified.

Risk recall matters more than raw risk precision because missing a genuinely risky case is more consequential than sending an extra case to human review.

### Routing Accuracy

Percentage of tickets routed to the expected automation/human path after deterministic policy is applied.

### Automation Rate

Percentage of benchmark tickets that become eligible for automatic processing.

This is not automatically a success metric. A very high automation rate combined with missed risks would be a failure.

### Human Override Rate

For tickets routed to review, percentage where the simulated or real reviewer changes the recommended outcome.

### Schema Success Rate

Percentage of provider responses that validate successfully without retry/fallback.

### Workflow Failure Rate

Percentage of benchmark runs ending in a recorded failure state.

### Latency

Capture at minimum:

- classification latency
- retrieval latency
- drafting latency
- end-to-end workflow latency

## Manual Baseline

The documented baseline contains eight manual actions per ticket.

RelayDesk will report step reduction only after the final workflow is functional. The comparison must distinguish:

- fully automated steps
- AI-assisted steps
- human-required steps

## Initial Quality Targets

These are engineering targets, not claimed results:

- category accuracy >= 90%
- routing accuracy >= 95%
- risk recall >= 95%
- schema success rate >= 98% after retry/fallback
- workflow failure rate < 2% in benchmark runs
- zero high-risk benchmark tickets auto-processed incorrectly

If a target is missed, the project should show the failure and the corrective iteration rather than hide it.

## Regression Testing

When prompts, models, routing rules, or retrieval behavior change, the benchmark dataset should be rerun.

A change should be flagged when it materially worsens:

- category accuracy
- risk recall
- routing accuracy
- schema success
- latency

## Failure Scenarios to Test

1. Provider unavailable
2. Provider timeout
3. Invalid JSON/structured response
4. Unknown category
5. Empty customer message
6. Oversized message
7. Retrieval returns nothing
8. Retrieval failure
9. Duplicate ticket
10. High-confidence model result with a deterministic risk override
11. Low-confidence routine request
12. Downstream action failure

## Reporting Rule

The portfolio may say:

> Benchmark result from a labeled synthetic dataset.

It may not imply that synthetic results are production-client outcomes.
