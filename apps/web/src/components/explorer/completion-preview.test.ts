import type { CameraPath, CompletionManifest } from "@dream-nav/shared";
import { describe, expect, it } from "vitest";
import {
  formatCompletionCacheStatus,
  selectNearestCachedCompletion
} from "./completion-preview";
import type { ViewerCameraPose } from "./viewer-camera";

const cameraPath: CameraPath = {
  scene_id: "warehouse_01",
  coordinate_system: "dreamnav_viewer_v1",
  intrinsics: {
    width: 1920,
    height: 1080,
    fx: 1240,
    fy: 1240,
    cx: 960,
    cy: 540
  },
  poses: [
    {
      frame_index: 0,
      timestamp_sec: 0,
      position: [0, 1.55, 0],
      rotation_xyzw: [0, 0, 0, 1],
      fov_degrees: 60
    },
    {
      frame_index: 24,
      timestamp_sec: 0.8,
      position: [1, 1.55, -2],
      rotation_xyzw: [0, 0, 0, 1],
      fov_degrees: 60
    }
  ]
};

const completion: CompletionManifest = {
  scene_id: "warehouse_01",
  model_enabled: true,
  architecture: "pose_conditioned_encoder_decoder",
  quality_gate: "warning",
  heldout_psnr_median: 21.4,
  cache_strategy: "planned_path",
  cached_predictions: [
    {
      prediction_id: "pred_001",
      camera_pose_index: 1,
      rgb_asset: "completion/pred_001.svg",
      confidence_mask_asset: null,
      latency_ms_p50: 12
    }
  ]
};

const currentPose: ViewerCameraPose = {
  fovDegrees: 54,
  lensMode: "35mm",
  pitch: 0,
  position: [1.1, 1.55, -2.2],
  yaw: 0
};

describe("completion preview selection", () => {
  it("selects the nearest cached prediction and resolves its asset URL", () => {
    const match = selectNearestCachedCompletion(
      completion,
      cameraPath,
      currentPose,
      "http://api.test/scenes/warehouse_01/"
    );

    expect(match?.prediction.prediction_id).toBe("pred_001");
    expect(match?.rgbUrl).toBe("http://api.test/scenes/warehouse_01/completion/pred_001.svg");
    expect(formatCompletionCacheStatus(completion, match)).toContain("pred_001");
  });

  it("supports same-origin proxied asset URLs", () => {
    const match = selectNearestCachedCompletion(
      completion,
      cameraPath,
      currentPose,
      "/dreamnav-assets/scenes/warehouse_01/"
    );

    expect(match?.rgbUrl).toBe("/dreamnav-assets/scenes/warehouse_01/completion/pred_001.svg");
  });

  it("disables cached completion when the quality gate fails", () => {
    const failedCompletion = {
      ...completion,
      quality_gate: "fail"
    } satisfies CompletionManifest;

    expect(
      selectNearestCachedCompletion(
        failedCompletion,
        cameraPath,
        currentPose,
        "http://api.test/scenes/warehouse_01/"
      )
    ).toBeNull();
    expect(formatCompletionCacheStatus(failedCompletion, null)).toBe("Disabled");
  });
});
