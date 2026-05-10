import { describe, expect, it } from "vitest";
import { buildSceneAssets, loadAllSceneBundles, loadDemoScenes, loadSceneBundle } from "./registry.js";

describe("scene registry", () => {
  it("loads locked demo scene listings", async () => {
    const scenes = await loadDemoScenes();

    expect(scenes.map((scene) => scene.scene_id)).toContain("warehouse_01");
  });

  it("builds API asset URLs for GET /scene/{scene_id}", () => {
    const assets = buildSceneAssets("warehouse_01");

    expect(assets.splat_url).toBe("/scenes/warehouse_01/splat.ply");
  });

  it("loads and validates every manifest for a scene", async () => {
    const bundle = await loadSceneBundle("warehouse_01");

    expect(bundle.metadata.scene_id).toBe("warehouse_01");
    expect(bundle.visibility.method).toBe("voxel_visibility_v1");
    expect(bundle.completion.cache_strategy).toBe("planned_path");
  });

  it("loads all registered scene bundles", async () => {
    const bundles = await loadAllSceneBundles();

    expect(bundles).toHaveLength(1);
  });

  it("fails clearly for unknown demo scenes", async () => {
    await expect(loadSceneBundle("missing_scene")).rejects.toThrow("Unknown demo scene");
  });
});
