import { describe, expect, it } from "vitest";
import { buildZoneArtifactsFromVisibility, zoneCells } from "./confidence-zones";

describe("confidence zones", () => {
  it("derives zone artifacts from visibility cells", () => {
    const zones = buildZoneArtifactsFromVisibility("scene_abc123", {
      scene_id: "scene_abc123",
      method: "voxel_visibility_v1",
      observed_threshold: 3,
      partial_threshold: [1, 2],
      observed_ratio: 0.5,
      partial_ratio: 0.25,
      completion_candidate_ratio: 0.25,
      unknown_ratio: 0,
      cells: [
        {
          cell_id: "cell_observed_001",
          center: [0, 1, -0.5],
          size_meters: 0.5,
          visibility_count: 4,
          zone: "observed"
        },
        {
          cell_id: "cell_completion_001",
          center: [1, 1, -1],
          size_meters: 0.5,
          visibility_count: 0,
          zone: "completion"
        }
      ]
    });

    expect(zones.observed.cell_count).toBe(1);
    expect(zones.completion.coverage_ratio).toBe(0.5);
    expect(zones.unknown.bounds).toBeNull();
    expect(zoneCells(zones)).toHaveLength(2);
  });
});
