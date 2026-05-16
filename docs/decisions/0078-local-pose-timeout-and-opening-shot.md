# 0078 Local Pose Timeout And Opening Shot

Date: 2026-05-17

## Decision

Scale the local COLMAP mapper timeout with extracted frame count and open processed scenes from an interior camera pose that looks toward the observed scene bounds instead of always starting from the first recovered frame.

## Why

Local uploads were repeatedly failing at the camera motion stage on medium phone clips because the mapper budget was fixed at 180 seconds even when COLMAP was still making progress. The processed viewer also opened from weak endpoint frames, which made accepted reconstructions look much worse than their actual coverage metrics.

## Consequences

Medium uploads get a larger mapper budget without slowing the lighter COLMAP steps, and processed scenes start from a more defensible framing by default. The tradeoff is that some local uploads now wait longer before failing and the opening shot heuristic is still geometric rather than fully visual.
