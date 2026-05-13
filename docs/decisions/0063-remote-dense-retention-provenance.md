# 0063 Remote Dense Retention And Provenance

## Decision

The remote dense worker now applies a retention rule to per job workspaces and the app now reads a typed remote dense result summary from `remote_dense_result.json`.

The worker keeps the newest remote job workspaces and prunes older `remote_*` directories based on `DREAMNAV_REMOTE_DENSE_RETAINED_JOBS`.

DreamNav now distinguishes between:

- the backend requested or reported at submission time
- the backend that actually produced the imported callback result

## Why

Per job isolation fixed concurrency safety, but the worker would still accumulate old job directories forever.

The UI also only showed submission provenance, which is weaker than callback provenance because a worker can fall back from a real backend to a mock backend internally.

## Consequences

Remote worker disk usage is now bounded by a configurable retention count.

The completed job review flow can now show the actual remote result backend and remote job id from the callback artifact, not just the initial submission metadata.

The remaining gap is dense reconstruction quality. Provenance is clearer, but this machine still falls back because the available COLMAP build cannot execute dense stereo.
