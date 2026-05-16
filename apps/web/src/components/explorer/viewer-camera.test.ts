import { describe, expect, it } from "vitest";
import { initialViewerCameraPose } from "./viewer-camera";

describe("initialViewerCameraPose", () => {
  it("uses the first camera path pose position and orientation", () => {
    const pose = initialViewerCameraPose(
      {
        scene_id: "scene_abc123",
        coordinate_system: "dreamnav_viewer_v1",
        intrinsics: {
          width: 1280,
          height: 720,
          fx: 910,
          fy: 910,
          cx: 640,
          cy: 360
        },
        poses: [
          {
            frame_index: 0,
            timestamp_sec: 0,
            position: [-6.79, 0.15, 1.17],
            rotation_xyzw: [0.031664548985274876, 0.6443458457509649, -0.06484259476617203, 0.7613220247076944],
            fov_degrees: 60
          }
        ]
      },
      "35mm"
    );

    expect(pose.position).toEqual([-6.79, 0.15, 1.17]);
    expect(pose.yaw).toBeGreaterThan(1.3);
    expect(pose.yaw).toBeLessThan(1.5);
    expect(pose.pitch).toBeGreaterThan(0.1);
    expect(pose.pitch).toBeLessThan(0.2);
  });

  it("falls back cleanly when rotation is missing", () => {
    const pose = initialViewerCameraPose(
      {
        scene_id: "scene_abc123",
        coordinate_system: "dreamnav_viewer_v1",
        intrinsics: {
          width: 1280,
          height: 720,
          fx: 910,
          fy: 910,
          cx: 640,
          cy: 360
        },
        poses: [
          {
            frame_index: 0,
            timestamp_sec: 0,
            position: [0, 1.55, 3],
            rotation_xyzw: [] as unknown as [number, number, number, number],
            fov_degrees: 60
          }
        ]
      },
      "35mm"
    );

    expect(pose.yaw).toBe(0);
    expect(pose.pitch).toBe(0);
  });
});
