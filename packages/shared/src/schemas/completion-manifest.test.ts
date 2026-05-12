import { describe, expect, it } from "vitest";
import { parseCompletionManifest } from "./completion-manifest.js";

describe("completion manifest schema", () => {
  it("accepts planned-path cached predictions", () => {
    const manifest = parseCompletionManifest({
      scene_id: "warehouse_01",
      model_enabled: true,
      architecture: "pose_conditioned_encoder_decoder",
      quality_gate: "warning",
      heldout_psnr_median: 21.4,
      cache_strategy: "planned_path",
      cache_version: "completion_cache_v1",
      cache_status: "ready",
      cached_predictions: [
        {
          prediction_id: "pred_001",
          camera_pose_index: 1,
          rgb_asset: "completion/pred_001.png",
          confidence_mask_asset: "completion/pred_001_mask.png",
          nearest_view_asset: "completion/baseline_nearest_001.png",
          nearest_view_camera_pose_index: 0,
          latency_ms_p50: 12,
          latency_ms_p95: 18,
          cache_key: "warehouse_01:pose_0001:v1",
          cache_status: "hit",
          cache_source: "planned_path",
          cache_reason: "Cached for planned demo path.",
          generated_at: "2026-05-12T00:00:00.000Z",
          runtime_path: "cached_output"
        }
      ]
    });

    expect(manifest.cached_predictions).toHaveLength(1);
    expect(manifest.cache_status).toBe("ready");
    expect(manifest.cached_predictions[0]?.latency_ms_p95).toBe(18);
  });

  it("adds defaults for legacy cache manifests", () => {
    const manifest = parseCompletionManifest({
      scene_id: "warehouse_01",
      model_enabled: true,
      architecture: "pose_conditioned_encoder_decoder",
      quality_gate: "warning",
      heldout_psnr_median: 21.4,
      cache_strategy: "planned_path",
      cached_predictions: [
        {
          prediction_id: "pred_001",
          camera_pose_index: 1,
          rgb_asset: "completion/pred_001.png",
          confidence_mask_asset: null,
          nearest_view_asset: null,
          nearest_view_camera_pose_index: null,
          latency_ms_p50: 12
        }
      ]
    });

    expect(manifest.cache_version).toBe("completion_cache_v1");
    expect(manifest.cache_status).toBe("empty");
    expect(manifest.cached_predictions[0]?.cache_status).toBe("hit");
  });
});
