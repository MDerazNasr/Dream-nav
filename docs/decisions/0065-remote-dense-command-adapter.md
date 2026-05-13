# 0065 Remote Dense Command Adapter

## Decision

The remote dense worker now supports a command backed dense engine adapter through `DREAMNAV_REMOTE_DENSE_BACKEND=command` and `DREAMNAV_REMOTE_DENSE_COMMAND`.

The command adapter contract is simple:

- DreamNav extracts the submission bundle into a per job workspace
- DreamNav invokes the configured executable with:
  - `--bundle-root`
  - `--artifacts-root`
  - `--frames-root`
  - `--output-ply`
- the adapter must write a `.ply` file at `--output-ply`

`auto` now prefers this command adapter when configured, then falls back to the built in COLMAP dense path, then to mock output when allowed.

## Why

The app and remote handoff plumbing are already in place. The next blocker is the real dense engine itself.

We need a stable integration seam so the first actual dense backend can be dropped into the remote worker without rewriting the app contract or callback flow again.

## Consequences

DreamNav now has a clean adapter surface for an external dense engine.

The next implementation step is no longer app plumbing. It is providing a real executable behind `DREAMNAV_REMOTE_DENSE_COMMAND` on a capable worker and validating the quality of its returned `.ply` output.
