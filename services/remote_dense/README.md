# DreamNav Remote Dense Worker

Local remote dense provider for the DreamNav handoff flow.

It accepts the DreamNav bundle zip, attempts a dense `.ply` build, and posts the result back to the configured DreamNav callback route.

Each remote job is unpacked into its own workspace under `.context/remote-dense-submissions/<remote_job_id>/`. The worker writes `bundle.zip`, extracted bundle contents, and a small `result.json` file with the backend that was actually used.

Backend selection:

- `DREAMNAV_REMOTE_DENSE_BACKEND=auto` tries the DreamNav COLMAP dense wrapper when the bundle includes COLMAP artifacts and the configured COLMAP build supports dense stereo. It falls back to the mock generator when that path is unavailable.
- `DREAMNAV_REMOTE_DENSE_BACKEND=colmap_dense` requires the real COLMAP dense path and returns an error instead of falling back.
- `DREAMNAV_REMOTE_DENSE_BACKEND=mock` always returns the local mock dense output.

Optional environment variables:

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
