# Nerfstudio Splatfacto Backend

Date: 2026-05-17

## Decision

Add a bundled `nerfstudio_splatfacto_backend.py` to the remote dense worker and make the Gaussian adapter prefer it when Nerfstudio command environment variables are configured.

## Why

The COLMAP dense to splat bridge has reached its practical visual limit for DreamNav. We need a trained Gaussian backend that fits the existing worker contract without forcing more app-side API changes.

## What Changed

- Added a repo-native Nerfstudio backend harness for `ns-train splatfacto` plus `ns-export gaussian-splat`.
- The backend writes a Nerfstudio `transforms.json` from DreamNav `camera_path.json`.
- The backend preserves real frame filenames instead of inferring synthetic names from frame indices.
- The backend materializes a `sparse_pc.ply` from COLMAP `points3D.txt` so Splatfacto can initialize from existing structure.
- The bundled Gaussian adapter now prefers the Nerfstudio backend when `DREAMNAV_NERFSTUDIO_TRAIN_COMMAND` or `DREAMNAV_NERFSTUDIO_EXPORT_COMMAND` is set.

## Consequences

- DreamNav can now drive a real Nerfstudio Gaussian training path on Runpod through the existing remote worker seam.
- The next reconstruction milestone is no longer worker plumbing. It is validating the real Nerfstudio trainer on the same benchmark walkthrough and comparing it against the current COLMAP bridge.
