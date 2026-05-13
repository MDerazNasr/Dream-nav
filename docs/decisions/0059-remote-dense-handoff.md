# 0059 Remote Dense Handoff

## Decision

Add a server-side remote dense submission route, a secure callback import route, and a completed-job UI panel that submits jobs to the remote worker without requiring a manual `.ply` upload step.

## Why

The local machine can process frames, poses, and sparse geometry, but it does not reliably produce dense scenes on its own. Manual dense import works, yet it keeps the dense backend outside the product workflow and leaves the handoff fragile.

## Consequences

Completed jobs can now be packaged into a remote dense bundle, sent to a configured provider, and imported back through a callback endpoint guarded by a shared token. The browser workflow surfaces submission state and watches for the returned dense review artifact so the imported result can appear in the normal processed-scene flow.
