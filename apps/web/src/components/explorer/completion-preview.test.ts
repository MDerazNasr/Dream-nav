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
  cache_version: "completion_cache_v1",
  cache_status: "ready",
  cached_predictions: [
    {
      prediction_id: "pred_001",
      camera_pose_index: 1,
      rgb_asset: "completion/pred_001.svg",
      confidence_mask_asset: "completion/pred_001_mask.svg",
      nearest_view_asset: "completion/baseline_nearest_001.png",
      nearest_view_camera_pose_index: 0,
      latency_ms_p50: 12,
      latency_ms_p95: 18,
      cache_key: "planned_path:warehouse_01:pose_0001:v1",
      cache_status: "hit",
      cache_source: "planned_path",
      cache_reason: "Cached during explorer preparation for the planned walkthrough path.",
      generated_at: "2026-05-12T00:00:00.000Z",
      runtime_path: "cached_output"
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
    expect(match?.maskUrl).toBe("http://api.test/scenes/warehouse_01/completion/pred_001_mask.svg");
    expect(match?.baselineUrl).toBe("http://api.test/scenes/warehouse_01/completion/baseline_nearest_001.png");
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
    expect(match?.maskUrl).toBe("/dreamnav-assets/scenes/warehouse_01/completion/pred_001_mask.svg");
    expect(match?.baselineUrl).toBe("/dreamnav-assets/scenes/warehouse_01/completion/baseline_nearest_001.png");
  });

  it("keeps the mask URL nullable when a cached prediction has no confidence mask", () => {
    const unmaskedCompletion = {
      ...completion,
      cached_predictions: [
        {
          camera_pose_index: 1,
          cache_key: "planned_path:warehouse_01:pose_0001:v1",
          cache_reason: "Cached during explorer preparation for the planned walkthrough path.",
          cache_source: "planned_path",
          cache_status: "hit",
          confidence_mask_asset: null,
          generated_at: "2026-05-12T00:00:00.000Z",
          latency_ms_p50: 12,
          latency_ms_p95: 18,
          nearest_view_asset: null,
          nearest_view_camera_pose_index: null,
          prediction_id: "pred_001",
          rgb_asset: "completion/pred_001.svg",
          runtime_path: "cached_output"
        }
      ]
    } satisfies CompletionManifest;

    const match = selectNearestCachedCompletion(
      unmaskedCompletion,
      cameraPath,
      currentPose,
      "http://api.test/scenes/warehouse_01/"
    );

    expect(match?.maskUrl).toBeNull();
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
