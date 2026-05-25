# DreamNav

DreamNav turns a short walkthrough video into a navigable 3D scene.

The current product has three major parts:
- a local web app for upload, processing, review, and scene exploration
- a local API that owns jobs, artifacts, scene bundles, and quality gates
- a remote GPU worker that runs Gaussian reconstruction training

## What It Does

Given a video, DreamNav:
- extracts frames
- recovers camera poses with COLMAP
- packages the reconstruction job for a remote worker
- trains a Gaussian scene on a GPU worker
- imports the result back into the app
- reviews the output before it becomes the active processed scene

## Current State

What is working:
- upload and local processing flow
- job-owned artifacts and scene bundles
- local web viewer and processed-scene workflow
- remote dense handoff to a Runpod GPU worker
- Gaussian training with Nerfstudio Splatfacto
- manual recovery and import when remote callback delivery fails
- reconstruction diagnostics and training-view quality tracking

What is not finished:
- reconstruction quality is still below product grade
- remote callback delivery is still fragile
- the current Gaussian path still needs more training-set cleanup and tuning

## Repo Layout

- `apps/web`
  - Next.js app for upload, workflow, explorer, and review UI
- `packages/shared`
  - shared schemas and contracts
- `services/api`
  - local FastAPI service that owns jobs and artifacts
- `services/remote_dense`
  - remote worker for dense and Gaussian reconstruction
- `docs/decisions`
  - architecture and implementation decisions
- `data`
  - local jobs, uploads, scenes, and generated artifacts

## Local Development

Requirements:
- Node 20+
- Python 3.12
- local virtualenv at `.venv`
- ffmpeg
- COLMAP for local pose recovery

Install:

```bash
npm install
npm run api:install
```

Run locally:

```bash
npm run api:dev
NEXT_PUBLIC_DREAMNAV_API_URL=http://127.0.0.1:8000 npm run dev -w @dream-nav/web -- --port 3001
```

Local URLs:
- web: `http://localhost:3001`
- api: `http://127.0.0.1:8000`

## Tests

Full project test run:

```bash
npm run test
```

Focused remote worker tests:

```bash
cd services/remote_dense
../../.venv/bin/python -m pytest tests/test_nerfstudio_splatfacto_backend.py tests/test_nerfstudio_diagnostics.py tests/test_backend.py tests/test_main.py -q
```

## Remote Reconstruction

The intended heavy reconstruction path is:
- local preprocessing on your machine
- remote Gaussian training on a GPU worker
- result import back into DreamNav

The current worker target is Runpod with:
- Nerfstudio Splatfacto
- official COLMAP ingestion path
- training-view diagnostics
- frame filtering based on COLMAP support
- consecutive-pose deduping for collapsed camera segments

## Progress

See [docs/progress-update.md](docs/progress-update.md) for the current short status.
