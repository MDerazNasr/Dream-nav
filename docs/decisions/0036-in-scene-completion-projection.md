# In Scene Completion Projection

The viewer now projects the nearest cached completion RGB output into the Three.js scene when the quality gate permits completion, matching the spec requirement that completion regions appear as model predicted content rather than only as a side panel preview.

The projection is intentionally anchored to the first completion-zone cell because the current cache stores planned-path predictions without a full textured surface or per-pixel depth registration.

