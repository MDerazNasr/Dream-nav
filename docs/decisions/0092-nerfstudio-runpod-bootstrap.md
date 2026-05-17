# Nerfstudio Runpod Bootstrap

Date: 2026-05-17

## Decision

Add repo-local bootstrap scripts for installing Nerfstudio on the GPU worker and starting the remote dense worker with the bundled Nerfstudio backend.

## Why

The reconstruction bottleneck has moved to the real Gaussian trainer. Runpod now has the right GPU, but the setup was still manual and fragile. We need a repeatable path that gets a worker from a raw CUDA image to a DreamNav-capable Nerfstudio worker.

## What Changed

- Added `services/remote_dense/scripts/install_nerfstudio_runpod.sh` to install `gsplat` and `nerfstudio` with the CUDA environment exported.
- Added `services/remote_dense/scripts/start_nerfstudio_worker.sh` to start the worker with the bundled Nerfstudio backend selected by default.

## Consequences

- We can bring up a real Gaussian worker on Runpod with two commands instead of ad hoc shell history.
- The next operational step is syncing the latest worker code to Runpod, running the install script there, and validating `/capabilities` before the first Splatfacto reconstruction trial.
