# 0060 Local Remote Dense Stub

## Decision

Add a dedicated local remote dense worker service that accepts DreamNav bundle uploads, generates a mock dense point cloud, and posts the result back through the existing remote callback route.

## Why

The application side of the remote dense handoff was ready, but there was still no runnable provider to validate the full submission and callback loop on one machine. Without a concrete worker, the remote integration would stay theoretical and hard to debug.

## Consequences

The repo now contains a local provider stub under `services/remote_dense`, along with run and test scripts. It is not a real reconstruction backend, but it gives DreamNav a working remote dense contract for end to end development, smoke tests, and future provider replacement.
