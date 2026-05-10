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
      cached_predictions: [
        {
          prediction_id: "pred_001",
          camera_pose_index: 1,
          rgb_asset: "completion/pred_001.png",
          confidence_mask_asset: "completion/pred_001_mask.png",
          latency_ms_p50: 12
        }
      ]
    });

    expect(manifest.cached_predictions).toHaveLength(1);
  });
});
