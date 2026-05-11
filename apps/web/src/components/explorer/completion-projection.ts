import type { CameraPath } from "@dream-nav/shared";
import * as THREE from "three";
import type { ConfidenceZoneArtifacts } from "../../lib/confidence-zones";

export type CompletionProjectionTarget = {
  cameraPoseIndex: number;
  maskUrl: string | null;
  url: string;
};

export type CompletionProjectionFrame = {
  distanceMeters: number;
  heightMeters: number;
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
  widthMeters: number;
};

export function createCompletionProjection(
  target: CompletionProjectionTarget,
  cameraPath: CameraPath,
  zoneArtifacts: ConfidenceZoneArtifacts
): THREE.Mesh {
  const frame = buildCompletionProjectionFrame(target, cameraPath, zoneArtifacts);
  const material = new THREE.MeshBasicMaterial({
    color: "#77d7c8",
    opacity: 0.88,
    side: THREE.DoubleSide,
    transparent: true
  });
  const projection = new THREE.Mesh(new THREE.PlaneGeometry(frame.widthMeters, frame.heightMeters), material);
  projection.name = "cached-completion-projection";
  projection.position.copy(frame.position);
  projection.quaternion.copy(frame.quaternion);
  projection.userData.cameraPoseIndex = target.cameraPoseIndex;
  projection.userData.distanceMeters = frame.distanceMeters;
  projection.userData.hasConfidenceMask = target.maskUrl !== null;

  new THREE.TextureLoader().load(target.url, (texture) => {
    texture.colorSpace = THREE.SRGBColorSpace;
    material.map = texture;
    material.color.set("#ffffff");
    material.needsUpdate = true;
  });

  if (target.maskUrl) {
    new THREE.TextureLoader().load(target.maskUrl, (texture) => {
      material.alphaMap = texture;
      material.alphaTest = 0.04;
      material.needsUpdate = true;
    });
  }

  return projection;
}

export function buildCompletionProjectionFrame(
  target: CompletionProjectionTarget,
  cameraPath: CameraPath,
  zoneArtifacts: ConfidenceZoneArtifacts
): CompletionProjectionFrame {
  const fallbackPose = cameraPath.poses[0];
  if (!fallbackPose) {
    throw new Error("Completion projection requires at least one camera pose.");
  }

  const targetPose = cameraPath.poses[target.cameraPoseIndex] ?? fallbackPose;
  const targetPosition = new THREE.Vector3(...targetPose.position);
  const targetQuaternion = new THREE.Quaternion(...targetPose.rotation_xyzw).normalize();
  const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(targetQuaternion).normalize();
  const completionCenter = completionZoneCenter(zoneArtifacts);
  const distanceMeters = projectionDistance(targetPosition, forward, completionCenter);
  const position = targetPosition.clone().addScaledVector(forward, distanceMeters);
  const heightMeters = 2 * Math.tan(THREE.MathUtils.degToRad(targetPose.fov_degrees) / 2) * distanceMeters;
  const widthMeters = heightMeters * cameraAspect(cameraPath);

  return {
    distanceMeters,
    heightMeters,
    position,
    quaternion: targetQuaternion,
    widthMeters
  };
}

function projectionDistance(
  targetPosition: THREE.Vector3,
  forward: THREE.Vector3,
  completionCenter: THREE.Vector3 | null
): number {
  if (!completionCenter) {
    return 1.8;
  }

  const offset = completionCenter.clone().sub(targetPosition);
  const forwardDistance = offset.dot(forward);
  const candidateDistance = forwardDistance > 0.4 ? forwardDistance : offset.length();
  return THREE.MathUtils.clamp(candidateDistance, 0.9, 4.5);
}

function completionZoneCenter(zoneArtifacts: ConfidenceZoneArtifacts): THREE.Vector3 | null {
  const cells = zoneArtifacts.completion.cells;
  if (cells.length === 0) {
    return null;
  }

  const center = cells.reduce(
    (sum, cell) =>
      sum.add(new THREE.Vector3(cell.center[0], Math.max(1.1, cell.center[1]), cell.center[2])),
    new THREE.Vector3()
  );
  return center.divideScalar(cells.length);
}

function cameraAspect(cameraPath: CameraPath): number {
  return cameraPath.intrinsics.width / cameraPath.intrinsics.height;
}
