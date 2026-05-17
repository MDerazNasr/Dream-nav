import type { CameraPath, LensMode } from "@dream-nav/shared";
import type { ConfidenceZoneArtifacts } from "../../lib/confidence-zones";
import { getLensFov } from "../../lib/lens";

export type ViewerCameraPose = {
  fovDegrees: number;
  lensMode: LensMode;
  pitch: number;
  position: [number, number, number];
  yaw: number;
};

export function initialViewerCameraPose(
  cameraPath: CameraPath,
  lensMode: LensMode,
  zoneArtifacts?: ConfidenceZoneArtifacts
): ViewerCameraPose {
  const sceneTarget = openingSceneTarget(zoneArtifacts);
  const overviewPosition = openingOverviewPosition(zoneArtifacts);
  const startPose = overviewPosition ? null : selectOpeningPose(cameraPath, sceneTarget);
  // Prefer a center looking opening shot so processed scenes do not start from a weak endpoint frame.
  const { pitch, yaw } = sceneTarget
    ? viewAnglesTowardTarget(overviewPosition ?? startPose?.position, sceneTarget) ?? rotationAngles(startPose?.rotation_xyzw)
    : rotationAngles(startPose?.rotation_xyzw);
  return {
    fovDegrees: getLensFov(lensMode),
    lensMode,
    pitch,
    position: [
      overviewPosition?.[0] ?? startPose?.position[0] ?? 0,
      overviewPosition?.[1] ?? startPose?.position[1] ?? 1.55,
      overviewPosition?.[2] ?? startPose?.position[2] ?? 3
    ],
    yaw
  };
}

function selectOpeningPose(
  cameraPath: CameraPath,
  sceneTarget: readonly [number, number, number] | null
) {
  if (!sceneTarget || cameraPath.poses.length <= 2) {
    return cameraPath.poses[0];
  }

  const firstCandidateIndex = Math.min(Math.floor(cameraPath.poses.length * 0.15), cameraPath.poses.length - 1);
  const lastCandidateIndex = Math.max(firstCandidateIndex, Math.ceil(cameraPath.poses.length * 0.85) - 1);
  const candidates = cameraPath.poses.slice(firstCandidateIndex, lastCandidateIndex + 1);
  const scoredCandidates = candidates
    .map((pose) => ({ pose, score: distanceSquared(pose.position, sceneTarget) }))
    .sort((left, right) => left.score - right.score);

  return scoredCandidates[0]?.pose ?? cameraPath.poses[0];
}

function openingSceneTarget(zoneArtifacts?: ConfidenceZoneArtifacts): [number, number, number] | null {
  const observedBounds = zoneArtifacts?.observed.bounds;
  if (observedBounds) {
    return midpoint(observedBounds.min, observedBounds.max);
  }

  const completionBounds = zoneArtifacts?.completion.bounds;
  if (completionBounds) {
    return midpoint(completionBounds.min, completionBounds.max);
  }

  return null;
}

function openingOverviewPosition(zoneArtifacts?: ConfidenceZoneArtifacts): [number, number, number] | null {
  const bounds = zoneArtifacts?.observed.bounds ?? zoneArtifacts?.completion.bounds;
  if (!bounds) {
    return null;
  }

  const center = midpoint(bounds.min, bounds.max);
  const spanX = bounds.max[0] - bounds.min[0];
  const spanY = bounds.max[1] - bounds.min[1];
  const spanZ = bounds.max[2] - bounds.min[2];
  // Use a compact fallback span so small reconstructed scenes do not open from meters away.
  const lateralSpan = Math.max(0.75, spanX, spanZ);
  return [
    center[0] - lateralSpan * 0.35,
    center[1] + Math.max(0.6, spanY * 0.6),
    bounds.max[2] + lateralSpan * 1.1
  ];
}

function midpoint(
  min: readonly [number, number, number],
  max: readonly [number, number, number]
): [number, number, number] {
  return [
    (min[0] + max[0]) / 2,
    (min[1] + max[1]) / 2,
    (min[2] + max[2]) / 2
  ];
}

function distanceSquared(
  position: readonly [number, number, number],
  target: readonly [number, number, number]
): number {
  const dx = target[0] - position[0];
  const dy = target[1] - position[1];
  const dz = target[2] - position[2];
  return dx * dx + dy * dy + dz * dz;
}

function viewAnglesTowardTarget(
  position: readonly [number, number, number] | undefined,
  target: readonly [number, number, number]
): { pitch: number; yaw: number } | null {
  if (!position) {
    return null;
  }

  const dx = target[0] - position[0];
  const dy = target[1] - position[1];
  const dz = target[2] - position[2];
  const horizontalDistance = Math.hypot(dx, dz);

  if (horizontalDistance < 0.001) {
    return null;
  }

  return {
    pitch: Math.atan2(dy, horizontalDistance),
    yaw: Math.atan2(dx, -dz)
  };
}

function rotationAngles(rotation: readonly number[] | undefined): { pitch: number; yaw: number } {
  if (!rotation || rotation.length !== 4) {
    return { pitch: 0, yaw: 0 };
  }

  const [x, y, z, w] = rotation as readonly [number, number, number, number];
  const matrix13 = 2 * (x * z + y * w);
  const matrix23 = 2 * (y * z - x * w);
  const matrix33 = 1 - 2 * (x * x + y * y);
  const matrix31 = 2 * (x * z - y * w);
  const matrix11 = 1 - 2 * (y * y + z * z);
  const clampedMatrix23 = Math.max(-1, Math.min(1, matrix23));
  const pitch = Math.asin(-clampedMatrix23);
  const yaw =
    Math.abs(matrix23) < 0.9999999 ? Math.atan2(matrix13, matrix33) : Math.atan2(-matrix31, matrix11);

  return { pitch, yaw };
}
