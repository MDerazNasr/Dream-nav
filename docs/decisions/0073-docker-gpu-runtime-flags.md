## Context

DreamNav had a CUDA image path, but the Docker adapter still launched containers without GPU or platform flags, which meant a GPU capable worker could still fail to expose the device or correct architecture to the dense engine.

## Decision

Add `DREAMNAV_REMOTE_DENSE_DOCKER_GPUS` and `DREAMNAV_REMOTE_DENSE_DOCKER_PLATFORM` support to the bundled Docker adapter and use those flags for both normal execution and the image health probe.

## Consequences

The CUDA image path is now runnable on a real GPU worker without changing the DreamNav command contract, and the readiness probe checks the same runtime shape that will be used for actual dense reconstruction.
