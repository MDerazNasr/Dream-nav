import type { CompletionManifest, QualityReport, SceneMetadata, VisibilityManifest } from "@dream-nav/shared";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { buildQualityReportText, QualityReportPanel } from "./QualityReportPanel";
import type { CachedCompletionMatch } from "./completion-preview";
import type { ViewerCameraPose } from "./viewer-camera";

const metadata = {
  scene_id: "warehouse_01",
  title: "Warehouse Scout",
  input_video: "warehouse_walkthrough.mp4",
  duration_sec: 32,
  frame_count: 742,
  pose_backend: "COLMAP",
  camera_path: "camera_path.json",
  splat_file: "splat.ply",
  visibility: {
    observed_threshold: 3,
    partial_threshold: [1, 2],
    observed_ratio: 0.62,
    partial_ratio: 0.22,
    completion_candidate_ratio: 0.11
  },
  scene_model: {
    enabled: true,
    architecture: "pose_conditioned_encoder_decoder",
    train_views: 520,
    heldout_views: 80,
    training_time_sec: 184,
    loss: "L_rgb + lambda_geo * L_geo",
    heldout_psnr_median: 21.4,
    quality_gate: "warning",
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
    splat_fps: 42,
    processing_time_sec: 258
  },
  product_tools: {
    lens_modes: ["24mm", "35mm", "50mm", "85mm"],
    camera_markers_enabled: true,
    notes_enabled: false
  }
} satisfies SceneMetadata;

const quality = {
  scene_id: "warehouse_01",
  pose_backend: "COLMAP",
  frame_count: 742,
  visibility_threshold_observed: 3,
  splat_fps: 42,
  scene_model_training_sec: 184,
  heldout_psnr_median: 21.4,
  quality_gate: "warning",
  completion_policy: "warning_overlay",
  quality_gate_reason: "Held-out PSNR is below 22 dB but at least 20 dB.",
  warning_threshold_psnr: 20,
  pass_threshold_psnr: 22,
  completion_latency_ms_p50: 68,
  completion_latency_ms_p95: 91,
  runtime_path: "torch_fp16",
  cached_completion: true
} satisfies QualityReport;

const completion = {
  scene_id: "warehouse_01",
  model_enabled: true,
  architecture: "pose_conditioned_encoder_decoder",
  quality_gate: "warning",
  heldout_psnr_median: 21.4,
  cache_strategy: "planned_path",
  cache_version: "completion_cache_v1",
  cache_status: "ready",
  cached_predictions: []
} satisfies CompletionManifest;

const visibility = {
  scene_id: "warehouse_01",
  method: "voxel_visibility_v1",
  observed_threshold: 3,
  partial_threshold: [1, 2],
  observed_ratio: 0.5,
  partial_ratio: 0.25,
  completion_candidate_ratio: 0.25,
  unknown_ratio: 0,
  cells: []
} satisfies VisibilityManifest;

const currentPose = {
  fovDegrees: 54,
  lensMode: "35mm",
  pitch: 0,
  position: [1, 1.55, -2],
  yaw: 0
} satisfies ViewerCameraPose;

const match = {
  baselineUrl: null,
  distanceMeters: 0.4,
  maskUrl: null,
  prediction: {
    prediction_id: "pred_001",
    camera_pose_index: 1,
    rgb_asset: "completion/pred_001.svg",
    confidence_mask_asset: null,
    nearest_view_asset: null,
    nearest_view_camera_pose_index: null,
    latency_ms_p50: 12,
    latency_ms_p95: 18,
    cache_key: "planned_path:warehouse_01:pose_0001:v1",
    cache_status: "hit",
    cache_source: "planned_path",
    cache_reason: "Cached during explorer preparation.",
    generated_at: "2026-05-12T00:00:00.000Z",
    runtime_path: "cached_output"
  },
  rgbUrl: "/dreamnav-assets/scenes/warehouse_01/completion/pred_001.svg"
} satisfies CachedCompletionMatch;

const remoteDenseResult = {
  job_id: "scene_abc123",
  remote_job_id: "remote_001",
  backend: "colmap_dense",
  source_file: "imports/remote_001.ply",
  validation_status: "pass",
  gaussian_count: 24000
} as const;

describe("QualityReportPanel", () => {
  it("builds a copyable quality report summary", () => {
    const report = buildQualityReportText({
      completion,
      currentPose,
      match,
      metadata,
      quality,
      remoteDenseResult,
      visibility
    });

    expect(report).toContain("DreamNav quality report: Warehouse Scout");
    expect(report).toContain("Held-out PSNR: 21.4 dB");
    expect(report).toContain("Prediction cache: hit · cached_output");
    expect(report).toContain("Current lens/FOV: 35mm / 54 deg");
    expect(report).toContain("Dense source: colmap_dense");
  });

  it("copies the quality report to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText }
    });

    render(
      <QualityReportPanel
        completion={completion}
        currentPose={currentPose}
        match={match}
        metadata={metadata}
        quality={quality}
        remoteDenseResult={remoteDenseResult}
        visibility={visibility}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Copy" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining("Warehouse Scout")));
    expect(screen.getByRole("button", { name: "Copied" })).not.toBeNull();
  });
});
