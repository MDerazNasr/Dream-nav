import type { CameraPath, QualityReport } from "@dream-nav/shared";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BaselineComparison, selectNearestReferenceView } from "./BaselineComparison";
import type { CachedCompletionMatch } from "./completion-preview";

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
    },
    {
      frame_index: 48,
      timestamp_sec: 1.6,
      position: [3, 1.55, -6],
      rotation_xyzw: [0, 0, 0, 1],
      fov_degrees: 60
    }
  ]
};

const quality: QualityReport = {
  scene_id: "warehouse_01",
  pose_backend: "COLMAP",
  frame_count: 742,
  visibility_threshold_observed: 3,
  splat_fps: 42,
  scene_model_training_sec: 184,
  heldout_psnr_median: 21.4,
  quality_gate: "warning",
  completion_latency_ms_p50: 68,
  completion_latency_ms_p95: 91,
  runtime_path: "torch_fp16",
  cached_completion: true
};

const match: CachedCompletionMatch = {
  baselineUrl: "/dreamnav-assets/scenes/warehouse_01/completion/baseline_nearest_001.svg",
  distanceMeters: 0.4,
  maskUrl: "/dreamnav-assets/scenes/warehouse_01/completion/pred_001_mask.svg",
  prediction: {
    prediction_id: "pred_001",
    camera_pose_index: 1,
    rgb_asset: "completion/pred_001.svg",
    confidence_mask_asset: "completion/pred_001_mask.svg",
    nearest_view_asset: "completion/baseline_nearest_001.svg",
    nearest_view_camera_pose_index: 0,
    latency_ms_p50: 12
  },
  rgbUrl: "/dreamnav-assets/scenes/warehouse_01/completion/pred_001.svg"
};

describe("BaselineComparison", () => {
  it("selects the nearest non-target camera pose as the baseline", () => {
    expect(selectNearestReferenceView(cameraPath, 1)).toEqual({
      cameraPoseIndex: 0,
      distanceMeters: expect.closeTo(2.236, 3),
      frameIndex: 0
    });
  });

  it("renders model prediction beside nearest-view baseline image", () => {
    render(<BaselineComparison cameraPath={cameraPath} match={match} quality={quality} />);

    expect(screen.getByLabelText("Baseline comparison")).not.toBeNull();
    expect(screen.getByAltText("Model completion comparison").getAttribute("src")).toBe(
      "/dreamnav-assets/scenes/warehouse_01/completion/pred_001.svg"
    );
    expect(screen.getByAltText("Nearest-view baseline comparison").getAttribute("src")).toBe(
      "/dreamnav-assets/scenes/warehouse_01/completion/baseline_nearest_001.svg"
    );
    expect(screen.getByText("DreamNav")).not.toBeNull();
    expect(screen.getByText("21.4 dB")).not.toBeNull();
    expect(screen.getByText("Nearest view")).not.toBeNull();
    expect(screen.getByText("Pose 1")).not.toBeNull();
  });
});
