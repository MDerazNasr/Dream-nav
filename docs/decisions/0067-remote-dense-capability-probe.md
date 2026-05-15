## Context

DreamNav can now submit completed jobs to a remote dense worker, but the app still needs a direct way to tell whether that worker can run a real dense backend before sending work to it.

## Decision

Add a `GET /capabilities` route to the remote dense worker that reports backend readiness, missing hard requirements, and softer warnings about the available dense paths.

## Consequences

Operators can verify whether a worker is real dense ready without submitting a job first, and DreamNav now has a stable probe it can consume later if we surface worker readiness in the product UI.
