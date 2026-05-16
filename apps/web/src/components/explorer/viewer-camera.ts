import type { CameraPath, LensMode } from "@dream-nav/shared";
import { getLensFov } from "../../lib/lens";

export type ViewerCameraPose = {
  fovDegrees: number;
  lensMode: LensMode;
  pitch: number;
  position: [number, number, number];
  yaw: number;
};

export function initialViewerCameraPose(cameraPath: CameraPath, lensMode: LensMode): ViewerCameraPose {
  const startPose = cameraPath.poses[0];
  // Respect the recovered capture orientation so processed scenes do not open facing away from the reconstruction.
  const { pitch, yaw } = rotationAngles(startPose?.rotation_xyzw);
  return {
    fovDegrees: getLensFov(lensMode),
    lensMode,
    pitch,
    position: [
      startPose?.position[0] ?? 0,
      startPose?.position[1] ?? 1.55,
      startPose?.position[2] ?? 3
    ],
    yaw
  };
}

function rotationAngles(rotation: readonly number[] | undefined): { pitch: number; yaw: number } {
  if (!rotation || rotation.length !== 4) {
    return { pitch: 0, yaw: 0 };
  }

  const [x, y, z, w] = rotation;
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
