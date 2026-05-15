## Context

DreamNav could submit completed jobs to a remote dense worker without first checking whether that worker was actually capable of producing a real dense result.

## Decision

Expose the worker readiness probe through the API, surface it in the completed-job workflow, and block remote submission when the worker is only capable of fallback output.

## Consequences

Operators can see why remote dense submission is blocked before they click, and the submission artifact now records the worker readiness snapshot that was used when the job was dispatched.
