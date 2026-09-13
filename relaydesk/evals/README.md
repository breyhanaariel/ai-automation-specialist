# RelayDesk Evaluation Harness

This folder contains the reproducible benchmark system for RelayDesk.

The benchmark dataset is `../data/support_tickets.jsonl`, a labeled synthetic set of 32 support tickets. Results produced by this harness must always be described as **benchmark results from a labeled synthetic dataset**, not production-client outcomes.

## What It Measures

- category accuracy
- priority accuracy
- risk recall
- routing accuracy
- schema success rate
- workflow failure rate
- automation rate
- high-risk auto-processing violations
- end-to-end latency
- classification, retrieval, and drafting latency when the API provides those stage timings

The report also includes a per-ticket breakdown so failures can be inspected instead of hidden inside aggregate percentages.

## Run a Live Benchmark

Start RelayDesk first:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Make sure the configured model/provider is available, then from `relaydesk/` run:

```bash
python -m evals.runner
```

The runner sends every labeled ticket through `POST /api/v1/process` and writes `evals/results/predictions.jsonl` and `evals/results/report.json`.

## Score Existing Predictions

To recompute a report without calling the model again:

```bash
python -m evals.runner --score-only
```

You can also provide alternate dataset, prediction, and report paths through the CLI flags.

## Truthfulness Rule

A report file is not proof that RelayDesk has production performance. It is evidence of a reproducible run against a synthetic benchmark. Portfolio copy should state the dataset size, model/provider, run date, and whether the result came from local or hosted inference.

CI tests the scoring calculations and dataset contract, but CI does **not** run Ollama or claim model-quality benchmark results.
