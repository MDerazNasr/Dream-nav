import { describe, expect, it } from "vitest";
import { parseZoneArtifact } from "./zone-artifact.js";

describe("zone artifact schema", () => {
  it("accepts split confidence zone files", () => {
    const artifact = parseZoneArtifact({
      scene_id: "warehouse_01",
      zone: "observed",
      source_manifest: "visibility_manifest.json",
      cell_count: 1,
      coverage_ratio: 0.25,
      bounds: {
        min: [0, 1, -0.5],
        max: [0.5, 1.5, 0]
      },
      cells: [
        {
          cell_id: "cell_001",
          center: [0.25, 1.25, -0.25],
          size_meters: 0.5,
          visibility_count: 4,
          zone: "observed"
        }
      ]
    });

    expect(artifact.zone).toBe("observed");
    expect(artifact.bounds?.min[1]).toBe(1);
  });

  it("accepts empty unknown zones", () => {
    const artifact = parseZoneArtifact({
      scene_id: "warehouse_01",
      zone: "unknown",
      source_manifest: "visibility_manifest.json",
      cell_count: 0,
      coverage_ratio: 0,
      bounds: null,
      cells: []
    });

    expect(artifact.cell_count).toBe(0);
  });
});
