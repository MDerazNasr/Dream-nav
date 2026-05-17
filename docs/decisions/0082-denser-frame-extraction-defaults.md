## Decision

The live upload pipeline now defaults to `4` FPS frame extraction, a `360` frame cap, and a `45` second frame extraction timeout.

## Why

The current reconstruction quality bottleneck is sparse source coverage, not browser rendering or remote dense handoff. The latest 29 second walkthrough only yielded about 59 extracted frames at the old `2` FPS default, which is too thin for stable room scale pose recovery and dense stereo.

## Consequence

Uploads will spend more time extracting frames and generate larger job artifacts, but the baseline reconstruction input is now materially denser before any COLMAP or dense backend tuning.
