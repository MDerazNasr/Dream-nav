import { describe, expect, it } from "vitest";
import {
  parseDemoReadiness,
  parseDemoScenesResponse,
  parseReconstructionCapabilities,
  parseSceneAssets
} from "./api-contracts.js";

describe("api contract schemas", () => {
  it("accepts demo scene listings from GET /demo-scenes", () => {
    const scenes = parseDemoScenesResponse([
      {
        scene_id: "warehouse_01",
        title: "Warehouse Scout",
        thumbnail_url: "/thumbs/warehouse_01.jpg",
        description: "Textured industrial space with partial corner completion"
      }
    ]);

    expect(scenes).toHaveLength(1);
  });

  it("accepts scene asset manifests from GET /scene/{scene_id}", () => {
    const assets = parseSceneAssets({
      scene_id: "warehouse_01",
      splat_url: "/scenes/warehouse_01/splat.ply",
      metadata_url: "/scenes/warehouse_01/metadata.json",
      visibility_manifest_url: "/scenes/warehouse_01/visibility_manifest.json",
      completion_manifest_url: "/scenes/warehouse_01/completion_manifest.json",
      quality_report_url: "/scenes/warehouse_01/quality.json"
    });

    expect(assets.quality_report_url).toBe("/scenes/warehouse_01/quality.json");
  });

  it("accepts demo readiness summaries from GET /demo-readiness/{scene_id}", () => {
    const readiness = parseDemoReadiness({
      scene_id: "warehouse_01",
      locked_scene: true,
      required_assets_present: true,
      fallback_assets_present: true,
      quality_gate: "warning",
      cached_completion: true,
      viewer_render_mode: "splat",
      status: "degraded",
      blockers: [],
      warnings: ["Completion must stay labeled as lower confidence."]
    });

    expect(readiness.status).toBe("degraded");
  });

  it("accepts reconstruction capability summaries from GET /reconstruction-capabilities", () => {
    const capabilities = parseReconstructionCapabilities({
      frame_backend: "ffmpeg",
      pose_backend: "stub",
      gaussian_backend: "stub",
      frame_command: "/opt/homebrew/bin/ffmpeg",
      pose_command: null,
      gaussian_command: null,
      pipeline_status: "mixed",
      real_reconstruction_ready: false,
      missing_requirements: [
        "Install COLMAP and set DREAMNAV_POSE_BACKEND=colmap.",
        "Set DREAMNAV_GAUSSIAN_BACKEND=command and DREAMNAV_GAUSSIAN_COMMAND to a real reconstruction wrapper."
      ],
      warnings: ["The current pipeline still falls back to placeholder geometry."]
    });

    expect(capabilities.pipeline_status).toBe("mixed");
  });
});
