import type { CameraPath, VisibilityManifest } from "@dream-nav/shared";
import { describe, expect, it } from "vitest";
import { buildZoneArtifactsFromVisibility } from "../../lib/confidence-zones";
import { buildCompletionProjectionFrame } from "./completion-projection";

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
      frame_index: 120,
      timestamp_sec: 5.2,
      position: [0.4, 1.55, -1.2],
      rotation_xyzw: [0, 0.08, 0, 0.997],
      fov_degrees: 60
    }
  ]
};

const visibility: VisibilityManifest = {
  scene_id: "warehouse_01",
  method: "voxel_visibility_v1",
  observed_threshold: 3,
  partial_threshold: [1, 2],
  observed_ratio: 0.5,
  partial_ratio: 0.25,
  completion_candidate_ratio: 0.25,
  unknown_ratio: 0,
  cells: [
    {
      cell_id: "cell_completion_001",
      center: [1.4, 1, -2.4],
      size_meters: 0.5,
      visibility_count: 0,
      zone: "completion"
    }
  ]
};

describe("completion projection", () => {
  it("uses the cached prediction camera pose to build a projected view plane", () => {
    const frame = buildCompletionProjectionFrame(
      { cameraPoseIndex: 1, url: "/completion/pred_001.svg" },
      cameraPath,
      buildZoneArtifactsFromVisibility("warehouse_01", visibility)
    );

    expect(frame.position.x).not.toBeCloseTo(1.4);
    expect(frame.position.z).toBeLessThan(-1.2);
    expect(frame.quaternion.y).toBeCloseTo(0.08, 2);
    expect(frame.widthMeters).toBeGreaterThan(frame.heightMeters);
    expect(frame.distanceMeters).toBeGreaterThan(0.9);
  });
});
