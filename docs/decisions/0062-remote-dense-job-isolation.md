# 0062 Remote Dense Job Isolation

## Decision

The remote dense worker now gives every submitted remote job its own workspace under `.context/remote-dense-submissions/<remote_job_id>/`.

Each job workspace contains:

- `bundle.zip`
- extracted bundle contents
- generated dense output files
- `result.json` with the backend actually used and any worker warnings

The callback path now also forwards backend provenance into DreamNav so completed job artifacts can record which remote backend produced the imported scene.

## Why

The previous worker reused one shared extraction directory for every submission. That was acceptable for a single local demo, but it would let overlapping jobs overwrite each other.

We also needed backend provenance to reach the app so the review UI can distinguish a true dense result from a fallback result.

## Consequences

Concurrent remote submissions no longer share extraction or output paths.

DreamNav now stores remote backend provenance in submission and result artifacts and exposes it in the completed-job remote dense review panel.

The remaining gap is lifecycle cleanup. Per-job workspaces now accumulate on disk until we add retention or explicit cleanup rules.
