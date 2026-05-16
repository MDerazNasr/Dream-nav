# 0075 Async Remote Dense Worker

## Decision

The remote dense worker now accepts `POST /jobs` submissions synchronously only through bundle validation and workspace creation, then performs dense reconstruction and callback delivery in a background task.

## Why

Real dense reconstruction on the GPU worker outlasts request timeout budgets, especially through Runpod proxy paths, so the worker must return control before the dense build finishes.

## Consequences

- Remote submission now reports queue acceptance rather than completed reconstruction.
- Per job `result.json` artifacts now track `submitted`, `running`, `completed`, or `failed`.
- Callback delivery and dense backend failures are recorded in the worker workspace instead of surfacing as request timeouts.
