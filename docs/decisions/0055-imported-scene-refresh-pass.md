# 0055 Imported Scene Refresh Pass

## Decision

Rebuild viewer-facing artifacts immediately after importing a Gaussian asset instead of only replacing `splat.ply`.

## Why

Visibility zones, quality summaries, and explorer bundles all depend on the active splat geometry. Leaving those artifacts stale after an import would make the scene appear denser while the confidence overlay, featured-scene gate, and viewer bundle still describe the previous reconstruction.

## Consequences

Imported scenes now refresh `visibility_manifest.json`, zone artifacts, `quality.json`, and `explorer_bundle.json` as part of the import route. This keeps featured-scene eligibility and explorer behavior tied to the imported geometry instead of the stale sparse asset it replaced.
