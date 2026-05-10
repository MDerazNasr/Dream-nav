import { describe, expect, it } from "vitest";
import { parseCameraPath } from "./camera-path.js";

describe("camera path schema", () => {
  it("accepts normalized viewer camera poses", () => {
    const path = parseCameraPath({
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
          position: [0, 1.5, 0],
          rotation_xyzw: [0, 0, 0, 1],
          fov_degrees: 60
        }
      ]
    });

    expect(path.poses[0]?.fov_degrees).toBe(60);
  });
});
