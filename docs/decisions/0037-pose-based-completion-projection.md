# Pose Based Completion Projection

Cached completion previews now project from the prediction camera pose recorded in `completion_manifest.json` because planned-path model output should remain tied to the target viewpoint used to generate it.

The viewer still uses a single textured plane until cached predictions include per-pixel depth or a surface registration artifact.

