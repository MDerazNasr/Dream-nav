# DreamNav Remote Dense Worker

Local remote dense provider for the DreamNav handoff flow.

It accepts the DreamNav bundle zip, attempts a dense `.ply` build, and posts the result back to the configured DreamNav callback route.

Each remote job is unpacked into its own workspace under `.context/remote-dense-submissions/<remote_job_id>/`. The worker writes `bundle.zip`, extracted bundle contents, and a small `result.json` file with submission status, backend, warnings, and any terminal error.

Submission model:

- `POST /jobs` returns immediately after the bundle is validated and written to disk.
- The dense build and callback run in the background from that saved workspace.
- `result.json` progresses through `submitted`, `running`, `completed`, or `failed`.

Retention:

- `DREAMNAV_REMOTE_DENSE_RETAINED_JOBS` controls how many remote job workspaces are kept on disk.
- Older `remote_*` workspaces are pruned automatically when a new submission is written.

Backend selection:

- `DREAMNAV_REMOTE_DENSE_BACKEND=gaussian_command` runs a trained Gaussian backend executable and is the preferred path for product-quality reconstruction once a true 3DGS engine is available.
- `DREAMNAV_REMOTE_DENSE_BACKEND=auto` tries a configured command backend first, then the DreamNav COLMAP dense wrapper, and falls back to the mock generator when those real paths are unavailable.
- `DREAMNAV_REMOTE_DENSE_BACKEND=command` runs the configured external dense engine command and requires it to write the output `.ply`.
- `DREAMNAV_REMOTE_DENSE_BACKEND=colmap_dense` requires the real COLMAP dense path and returns an error instead of falling back.
- `DREAMNAV_REMOTE_DENSE_BACKEND=mock` always returns the local mock dense output.

First real adapter executable in this repo:

- `services/remote_dense/remote_dense_app/colmap_command_adapter.py`
- the worker now uses this bundled adapter by default when `DREAMNAV_REMOTE_DENSE_COMMAND` is not set

Containerized engine adapter:

- `services/remote_dense/remote_dense_app/docker_command_adapter.py`
- if `DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE` is set, the worker now prefers this bundled Docker adapter by default
- the container image must implement the same DreamNav dense command contract and accept `--bundle-root`, `--artifacts-root`, `--frames-root`, and `--output-ply`
- the worker now probes the container with `--health-check` before treating it as real-dense ready

Optional environment variables:

- `DREAMNAV_REMOTE_GAUSSIAN_COMMAND` points to a trained Gaussian backend executable. DreamNav calls it with `--bundle-root`, `--artifacts-root`, `--frames-root`, and `--output-ply`. `auto` prefers this path before the older point cloud bridge.
- `DREAMNAV_REMOTE_DENSE_COMMAND` points to an external dense engine adapter executable. DreamNav calls it with `--bundle-root`, `--artifacts-root`, `--frames-root`, and `--output-ply`.
- Command backends can now emit either a DreamNav-ready splat PLY or a standard dense point-cloud PLY. The worker normalizes point-cloud output into the viewer splat format before callback import.
- `DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE` selects a container image for the bundled Docker adapter.
- `DREAMNAV_REMOTE_DENSE_DOCKER_RUNTIME` overrides the container runtime binary and defaults to `docker`.
- `DREAMNAV_REMOTE_DENSE_DOCKER_GPUS` passes a value to `docker run --gpus`. Set this to `all` on a GPU worker when using the CUDA image.
- `DREAMNAV_REMOTE_DENSE_DOCKER_PLATFORM` passes a value to `docker run --platform`. This is useful when the worker host and image architecture differ.
- `DREAMNAV_REMOTE_DENSE_DOCKER_BUILD_PLATFORM` controls the platform used by `npm run remote-dense:image:build:cuda`. It defaults to `linux/amd64` because the intended dense worker target is an NVIDIA Linux host, not the architecture of the machine that kicked off the build.
- `DREAMNAV_REMOTE_DENSE_COLMAP_COMMAND` selects the COLMAP binary to use for dense capability checks and wrapper execution.
- `DREAMNAV_REMOTE_DENSE_ALLOW_MOCK_FALLBACK=0` disables auto fallback when `backend=auto`.
- `DREAMNAV_REMOTE_DENSE_CALLBACK_TIMEOUT_SEC` controls the callback request timeout.

Capability probe:

- `GET /capabilities` reports whether the worker is actually ready to run a real dense backend.
- `real_dense_ready=true` means the worker can use either a trained Gaussian backend, a valid command adapter, or a supported COLMAP dense path.
- `gaussian_backend_ready=true` means the worker has a configured trained Gaussian executable and `auto` can prefer it ahead of the point-cloud bridge.
- `missing_requirements` lists hard blockers such as a missing command executable or no real dense backend on the machine.
- `warnings` reports softer issues such as a COLMAP build that cannot run dense stereo while a command adapter is still available.

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

Build the reference engine image:

```bash
npm run remote-dense:image:build
```

Build the CUDA engine image on a GPU worker:

```bash
npm run remote-dense:image:build:cuda
```

Override the CUDA image build platform when needed:

```bash
DREAMNAV_REMOTE_DENSE_DOCKER_BUILD_PLATFORM=linux/amd64 npm run remote-dense:image:build:cuda
```

Current state:

- `remote-dense:image:build` produces a reference Ubuntu image that is useful for validating the container contract and health probe, but it still installs a CPU only COLMAP build.
- `remote-dense:image:build:cuda` is the intended path for a real dense capable worker because it builds COLMAP with CUDA enabled from source.
