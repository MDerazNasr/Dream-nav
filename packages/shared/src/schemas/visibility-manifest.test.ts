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
});
