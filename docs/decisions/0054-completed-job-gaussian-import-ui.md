# 0054 Completed Job Gaussian Import UI

## Decision

Expose manual dense asset import on the completed-job processing screen instead of the initial upload screen.

## Why

The import flow depends on artifacts that only exist after a job has already finished frame extraction, pose recovery, visibility computation, and viewer preparation. Attaching the control to completed jobs keeps the data flow clear and avoids implying that a raw upload can skip the existing camera-path and manifest pipeline.

## Consequences

Users can replace a sparse reconstruction with an imported dense `.ply` directly from the finished job view and open it immediately in the explorer. The upload screen stays focused on walkthrough ingestion instead of mixing two unrelated entry points.
