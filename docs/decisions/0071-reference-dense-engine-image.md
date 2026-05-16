## Context

DreamNav had a Docker adapter, but it still lacked a concrete engine image contract and a trustworthy way to distinguish a merely configured image from one that can actually run dense stereo.

## Decision

Add a reference dense-engine Dockerfile, teach the bundled COLMAP adapter to answer `--health-check`, and have the Docker adapter probe that health check before the worker reports real-dense readiness.

## Consequences

DreamNav now has a concrete image target for `DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE`, and worker readiness can reject container images whose bundled COLMAP build still cannot execute dense stereo.
