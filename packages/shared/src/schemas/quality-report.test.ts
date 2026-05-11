import { describe, expect, it } from "vitest";
import { parseQualityReport } from "./quality-report.js";

describe("quality report schema", () => {
  it("accepts measured scene metrics from GET /quality/{scene_id}", () => {
    const report = parseQualityReport({
      scene_id: "warehouse_01",
      pose_backend: "COLMAP",
      frame_count: 742,
      visibility_threshold_observed: 3,
      splat_fps: 42,
      scene_model_training_sec: 184,
      heldout_psnr_median: 24.7,
      quality_gate: "pass",
      completion_policy: "enabled",
      quality_gate_reason: "Held-out PSNR meets the 22 dB pass threshold.",
      warning_threshold_psnr: 20,
      pass_threshold_psnr: 22,
      completion_latency_ms_p50: 68,
      completion_latency_ms_p95: 91,
      runtime_path: "torch_fp16",
      cached_completion: true
    });

    expect(report.quality_gate).toBe("pass");
    expect(report.completion_policy).toBe("enabled");
  });
});
