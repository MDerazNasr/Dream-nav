## Decision

Dense point cloud imports now use a tighter adaptive splat scale cap and visibility sampling reads evenly across the full splat instead of only the first rows.

## Why

The denser `117` frame reconstruction was still rendering as a blurred splat mass, and large imports could also be mis-scored because visibility only inspected the first `512` rows of the splat. The current dense input needs a smaller scale envelope and a more representative visibility sample before we can judge it honestly.

## Consequence

Dense imports remain rough, but the viewer no longer inflates many points to the previous oversized cap and the quality gate now reflects the full imported splat distribution more accurately.
