# 0064 Processed Scene Provenance

## Decision

Processed job scene bundles now include the optional `remote_dense_result` artifact when one exists, and the explorer quality report surfaces that provenance after the scene is opened.

This provenance includes:

- remote dense backend
- remote dense job id
- imported source file
- callback validation status

## Why

The completed-job workflow already showed submission and callback provenance before opening the explorer, but that context was lost once the processed scene was opened.

If a user is judging reconstruction quality, the explorer should make it clear whether the current scene came from a remote dense import and which backend actually produced it.

## Consequences

Processed scenes now carry reconstruction provenance into the explorer and copyable quality report output.

This is the last app-side visibility gap for the remote dense flow. The main remaining work is reconstruction quality, not workflow clarity.
