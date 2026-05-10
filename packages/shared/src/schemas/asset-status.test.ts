import { describe, expect, it } from "vitest";
import { parseSceneAssetStatus } from "./asset-status.js";

describe("scene asset status schema", () => {
  it("accepts placeholder mode when the splat is unavailable", () => {
    const status = parseSceneAssetStatus({
      scene_id: "warehouse_01",
      splat_url: "/scenes/warehouse_01/splat.ply",
      splat_available: false,
      viewer_render_mode: "placeholder",
      missing_assets: ["splat.ply"]
    });

    expect(status.viewer_render_mode).toBe("placeholder");
  });

  it("rejects unsupported render modes", () => {
    expect(() =>
      parseSceneAssetStatus({
        scene_id: "warehouse_01",
        splat_url: "/scenes/warehouse_01/splat.ply",
        splat_available: true,
        viewer_render_mode: "mesh",
        missing_assets: []
      })
    ).toThrow();
  });
});
