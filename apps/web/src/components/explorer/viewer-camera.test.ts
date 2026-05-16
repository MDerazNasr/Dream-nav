import { describe, expect, it } from "vitest";
import { initialViewerCameraPose } from "./viewer-camera";

describe("initialViewerCameraPose", () => {
  it("uses the first camera path pose position and orientation when no scene target is available", () => {
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

  it("prefers an interior opening pose and looks toward the observed scene bounds", () => {
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
            position: [-10, 1.55, 0],
            rotation_xyzw: [0, 0, 0, 1],
            fov_degrees: 60
          },
          {
            frame_index: 1,
            timestamp_sec: 0.5,
            position: [-2, 1.55, 0],
            rotation_xyzw: [0, 0, 0, 1],
            fov_degrees: 60
          },
          {
            frame_index: 2,
            timestamp_sec: 1,
            position: [0, 1.55, 0],
            rotation_xyzw: [0, 0, 0, 1],
            fov_degrees: 60
          },
          {
            frame_index: 3,
            timestamp_sec: 1.5,
            position: [2, 1.55, 0],
            rotation_xyzw: [0, 0, 0, 1],
            fov_degrees: 60
          },
          {
            frame_index: 4,
            timestamp_sec: 2,
            position: [10, 1.55, 0],
            rotation_xyzw: [0, 0, 0, 1],
            fov_degrees: 60
          }
        ]
      },
      "35mm",
      {
        observed: {
          scene_id: "scene_abc123",
          zone: "observed",
          source_manifest: "visibility_manifest.json",
          cell_count: 10,
          coverage_ratio: 0.8,
          bounds: {
            min: [-1, 1, 5],
            max: [1, 3, 7]
          },
          cells: []
        },
        partial: {
          scene_id: "scene_abc123",
          zone: "partial",
          source_manifest: "visibility_manifest.json",
          cell_count: 0,
          coverage_ratio: 0,
          bounds: null,
          cells: []
        },
        completion: {
          scene_id: "scene_abc123",
          zone: "completion",
          source_manifest: "visibility_manifest.json",
          cell_count: 0,
          coverage_ratio: 0,
          bounds: null,
          cells: []
        },
        unknown: {
          scene_id: "scene_abc123",
          zone: "unknown",
          source_manifest: "visibility_manifest.json",
          cell_count: 0,
          coverage_ratio: 0,
          bounds: null,
          cells: []
        }
      }
    );

    expect(pose.position[0]).toBeCloseTo(-0.7, 5);
    expect(pose.position[1]).toBeCloseTo(3.25, 5);
    expect(pose.position[2]).toBeCloseTo(9.2, 5);
    expect(pose.yaw).toBeGreaterThan(0.2);
    expect(pose.yaw).toBeLessThan(0.25);
    expect(pose.pitch).toBeLessThan(-0.3);
    expect(pose.pitch).toBeGreaterThan(-0.4);
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
