import { describe, expect, it } from "vitest";
import { parseVisibilityManifest } from "./visibility-manifest.js";

describe("visibility manifest schema", () => {
  it("accepts voxel visibility support for overlay zones", () => {
    const manifest = parseVisibilityManifest({
      scene_id: "warehouse_01",
      method: "voxel_visibility_v1",
      observed_threshold: 3,
      partial_threshold: [1, 2],
      observed_ratio: 0.62,
      partial_ratio: 0.22,
      completion_candidate_ratio: 0.11,
      unknown_ratio: 0.05,
      cells: [
        {
          cell_id: "cell_001",
          center: [0, 1, 0],
          size_meters: 0.5,
          visibility_count: 4,
          zone: "observed"
        }
      ]
    });

    expect(manifest.cells[0]?.zone).toBe("observed");
  });

  it("accepts adaptive voxel visibility support metadata", () => {
    const manifest = parseVisibilityManifest({
      scene_id: "scene_abc123",
      method: "voxel_visibility_v1_adaptive",
      observed_threshold: 3,
      partial_threshold: [1, 2],
      observed_ratio: 0.875,
      partial_ratio: 0.0312,
      completion_candidate_ratio: 0.0938,
      unknown_ratio: 0,
      adaptive_thresholds: {
        near_radius_meters: 9.382,
        far_radius_meters: 10.882
      },
      cells: [
        {
          cell_id: "cell_001",
          center: [8.1, -1.6, 7.5],
          size_meters: 0.5,
          visibility_count: 21,
          zone: "observed"
        }
      ]
    });

    expect(manifest.method).toBe("voxel_visibility_v1_adaptive");
    expect(manifest.adaptive_thresholds?.near_radius_meters).toBe(9.382);
  });
});
