# DreamNav Remote Dense Worker

Local remote dense provider for the DreamNav handoff flow.

It accepts the DreamNav bundle zip, attempts a dense `.ply` build, and posts the result back to the configured DreamNav callback route.

Each remote job is unpacked into its own workspace under `.context/remote-dense-submissions/<remote_job_id>/`. The worker writes `bundle.zip`, extracted bundle contents, and a small `result.json` file with the backend that was actually used.

Retention:

- `DREAMNAV_REMOTE_DENSE_RETAINED_JOBS` controls how many remote job workspaces are kept on disk.
- Older `remote_*` workspaces are pruned automatically when a new submission is written.

Backend selection:

- `DREAMNAV_REMOTE_DENSE_BACKEND=auto` tries a configured command backend first, then the DreamNav COLMAP dense wrapper, and falls back to the mock generator when those real paths are unavailable.
- `DREAMNAV_REMOTE_DENSE_BACKEND=command` runs the configured external dense engine command and requires it to write the output `.ply`.
- `DREAMNAV_REMOTE_DENSE_BACKEND=colmap_dense` requires the real COLMAP dense path and returns an error instead of falling back.
- `DREAMNAV_REMOTE_DENSE_BACKEND=mock` always returns the local mock dense output.

Optional environment variables:

- `DREAMNAV_REMOTE_DENSE_COMMAND` points to an external dense engine adapter executable. DreamNav calls it with `--bundle-root`, `--artifacts-root`, `--frames-root`, and `--output-ply`.
- `DREAMNAV_REMOTE_DENSE_COLMAP_COMMAND` selects the COLMAP binary to use for dense capability checks and wrapper execution.
- `DREAMNAV_REMOTE_DENSE_ALLOW_MOCK_FALLBACK=0` disables auto fallback when `backend=auto`.
- `DREAMNAV_REMOTE_DENSE_CALLBACK_TIMEOUT_SEC` controls the callback request timeout.

Run tests:

```bash
npm run remote-dense:test
```

Start the worker:

```bash
npm run remote-dense:dev
```

Default local address:

```txt
http://127.0.0.1:8010
```
