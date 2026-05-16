## Context

The first reference Docker image validated the DreamNav container contract, but it still used a CPU only Ubuntu COLMAP package and therefore failed the dense stereo health check.

## Decision

Keep the CPU image as a contract and probe reference, add a separate CUDA image path that builds COLMAP with CUDA enabled from source, and tighten CUDA failure detection so the worker reports the reason clearly.

## Consequences

DreamNav now has an explicit GPU worker build target for real dense reconstruction, while the existing CPU image still serves as a reproducible negative control for the readiness gate.
