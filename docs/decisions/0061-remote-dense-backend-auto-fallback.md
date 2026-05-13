# 0061 Remote Dense Backend Auto Fallback

## Decision

The remote dense worker now accepts DreamNav bundles with packaged COLMAP artifacts and supports backend selection through `DREAMNAV_REMOTE_DENSE_BACKEND`.

`auto` is the default mode. It attempts the real DreamNav COLMAP dense wrapper when the bundle includes COLMAP sparse artifacts and the configured COLMAP build supports dense stereo. If either condition fails, it falls back to the existing mock dense generator unless fallback is explicitly disabled.

`colmap_dense` forces the real dense path and returns an error when the worker cannot execute it.

`mock` keeps the old behavior for deterministic local testing and fallback demos.

## Why

The app side remote dense handoff is already working end to end. The next step is to let the worker grow into a real reconstruction provider without breaking the current demo flow on machines that cannot run COLMAP dense stereo.

This machine still uses a COLMAP build without dense stereo support, so the worker needs a controlled fallback path while preserving a real backend contract for CUDA capable environments.

## Consequences

Completed jobs can now ship their COLMAP artifacts to the remote worker, and the worker can attempt a real dense build without changing the submit or callback API.

Local development stays usable because unsupported environments fall back automatically instead of failing every submission.

The remaining gap is reconstruction quality. A CUDA capable or otherwise dense capable environment is still required before the remote worker can replace mock output with a genuinely dense scene on every job.
