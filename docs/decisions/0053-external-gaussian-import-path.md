# 0053 External Gaussian Import Path

## Decision

Add a completed-job Gaussian import route that accepts an external `.ply`, normalizes it into `splat.ply`, and reuses the existing viewer bundle instead of coupling dense reconstruction to the local processing worker.

## Why

The current laptop can run real frame extraction and pose recovery, but it cannot execute dense stereo locally with the installed COLMAP build. A manual import path keeps the product flow moving by letting a remote or alternate backend produce the dense asset while DreamNav continues to own camera paths, visibility manifests, quality gates, and browser rendering.

## Consequences

Completed jobs can now swap sparse reconstructions for imported dense assets without changing the scene bundle contract. Imported scenes are also allowed through the featured-scene quality gate when they meet the same Gaussian count, observed coverage, and quality thresholds as locally generated scenes.
