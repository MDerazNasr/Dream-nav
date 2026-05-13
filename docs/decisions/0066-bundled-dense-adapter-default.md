# 0066 Bundled Dense Adapter Default

## Decision

The remote dense worker now defaults `DREAMNAV_REMOTE_DENSE_COMMAND` to the bundled executable at `services/remote_dense/remote_dense_app/colmap_command_adapter.py` when no explicit command is configured.

`auto` therefore prefers a real command-backed dense path out of the box before falling back to the built in `colmap_dense` branch or mock output.

## Why

We already added a command adapter contract and the first real executable in the repo. Requiring an extra manual environment variable just to use the bundled adapter adds unnecessary setup friction.

The worker should prefer the real executable path by default whenever the repo already contains it.

## Consequences

On a capable worker, DreamNav can now attempt the bundled command-backed dense path without extra configuration.

On this machine, the bundled adapter still falls back indirectly because the available COLMAP build cannot execute dense stereo. That is an environment limitation, not another integration gap.
