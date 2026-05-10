import { describe, expect, it } from "vitest";
import { parseSceneMetadata } from "./scene-metadata.js";

const validSceneMetadata = {
  scene_id: "warehouse_01",
  title: "Warehouse Scout",
  input_video: "warehouse_walkthrough.mp4",
  duration_sec: 32,
  frame_count: 960,
  pose_backend: "COLMAP",
  camera_path: "camera_path.json",
  splat_file: "splat.ply",
  visibility: {
    observed_threshold: 3,
    partial_threshold: [1, 2],
    observed_ratio: 0.71,
    partial_ratio: 0.18,
    completion_candidate_ratio: 0.11
  },
  scene_model: {
    enabled: true,
    architecture: "pose_conditioned_encoder_decoder",
    train_views: 520,
    heldout_views: 80,
    training_time_sec: 176,
    loss: "L_rgb + lambda_geo * L_geo",
    heldout_psnr_median: 24.1,
    quality_gate: "pass",
    lpips: null
  },
  optimization: {
    fp32_latency_ms_p50: null,
    fp16_latency_ms_p50: 68,
    compiled_latency_ms_p50: null,
    tensorrt_latency_ms_p50: null,
    cached_output_latency_ms_p50: 12
  },
  zones: {
    observed: "observed_zone.json",
    partial: "partial_zone.json",
    completion: "completion_zone.json",
    unknown: "unknown_zone.json"
  },
  quality: {
    capture_score: 0.84,
    sharpness_score: 0.79,
    parallax_score: 0.88,
    texture_score: 0.81,
    splat_fps: 47,
    processing_time_sec: 258
  },
  product_tools: {
    lens_modes: ["24mm", "35mm", "50mm", "85mm"],
    camera_markers_enabled: true,
    notes_enabled: false
  }
};

describe("scene metadata schema", () => {
  it("accepts the manifest shape defined by the project spec", () => {
    expect(parseSceneMetadata(validSceneMetadata).scene_id).toBe("warehouse_01");
  });

  it("rejects ratios outside the valid confidence range", () => {
    const invalidMetadata = {
      ...validSceneMetadata,
      visibility: {
        ...validSceneMetadata.visibility,
        observed_ratio: 1.4
      }
    };

    expect(() => parseSceneMetadata(invalidMetadata)).toThrow();
  });

  it("rejects scene assets that escape the scene root", () => {
    const invalidMetadata = {
      ...validSceneMetadata,
      splat_file: "../splat.ply"
    };

    expect(() => parseSceneMetadata(invalidMetadata)).toThrow();
  });
});
