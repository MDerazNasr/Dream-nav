## Context

DreamNav needs a practical path to run a real dense engine on a capable worker without requiring the host machine to install every engine-specific dependency directly.

## Decision

Add a bundled Docker command adapter that runs a container image implementing the DreamNav dense command contract, and prefer that adapter automatically when `DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE` is configured.

## Consequences

CUDA capable workers can host real dense engines behind a container boundary while keeping the DreamNav worker contract unchanged, and the readiness probe can now block submission when the Docker image or runtime is missing.
