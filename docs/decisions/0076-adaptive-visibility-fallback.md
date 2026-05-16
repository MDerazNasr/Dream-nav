# 0076 Adaptive Visibility Fallback

## Decision

The visibility manifest builder now falls back to adaptive room scale distance bands when the fixed near camera heuristic collapses into almost all completion cells for a sufficiently large dense splat.

## Why

The original fixed `1.2m` and `2.4m` support radii were tuned for placeholder and near path mock geometry, but real dense reconstructions can be several meters from the nearest camera pose while still being correctly aligned and visually usable.

## Consequences

- Real dense imports are no longer falsely rejected purely because the visibility heuristic assumed a much smaller scene scale.
- The fallback only activates when the fixed heuristic produces zero observed coverage and nearly all cells fall into completion.
- Visibility manifests now annotate the adaptive radii that were used when this fallback path activates.
