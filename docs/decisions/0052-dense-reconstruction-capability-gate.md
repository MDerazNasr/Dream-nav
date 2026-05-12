# 0052 Dense Reconstruction Capability Gate

## Decision

Keep the sparse COLMAP to splat wrapper as the default Gaussian command, and expose dense reconstruction readiness separately from general real-pipeline readiness.

## Why

The local Homebrew COLMAP build on this machine reports `without CUDA`, and `patch_match_stereo` aborts during dense stereo reconstruction. Promoting the dense wrapper to the default command would make new uploads fail even though the rest of the real pipeline is configured.

## Consequences

The app can honestly report two states at once: the upload pipeline is real, and dense reconstruction is still unavailable on the current machine. The dense COLMAP wrapper remains available for explicit use on machines with a compatible COLMAP build or a future alternate dense backend.
