## Decision

The CUDA remote dense image build now defaults to `linux/amd64` through `DREAMNAV_REMOTE_DENSE_DOCKER_BUILD_PLATFORM`.

## Why

The dense worker target is a Linux NVIDIA host, but image builds may be kicked off from Apple Silicon or other non target machines. Defaulting the build to the caller's host architecture makes the CUDA image path ambiguous and can silently produce the wrong artifact for the real worker.

## Consequence

Operators can still override the build platform explicitly, but the default build command now matches the intended dense worker deployment shape.
