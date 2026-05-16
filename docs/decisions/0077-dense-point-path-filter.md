# 0077 Dense Point Path Filter

## Decision

The COLMAP dense wrapper now filters fused points against the recovered camera path before converting them into DreamNav splats.

## Why

The raw fused dense cloud can include large off-path point clusters that technically render but open far away from the walkthrough and degrade the first-view experience.

## Consequences

- Future remote dense imports should contain fewer far-field artifacts.
- The dense wrapper now uses the `camera_path.json` argument it already received instead of ignoring it.
- Filtering is conservative and distance based, so it can be tightened further if later runs still show large unsupported clusters.
