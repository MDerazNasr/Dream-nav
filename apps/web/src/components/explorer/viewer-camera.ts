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
  return {
    fovDegrees: getLensFov(lensMode),
    lensMode,
    pitch: 0,
    position: [
      startPose?.position[0] ?? 0,
      startPose?.position[1] ?? 1.55,
      startPose?.position[2] ?? 3
    ],
    yaw: 0
  };
}
