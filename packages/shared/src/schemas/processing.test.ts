import { describe, expect, it } from "vitest";
import { parseJobArtifact, parseJobSceneBundle, parseJobStatus, parseUploadResponse } from "./processing.js";

describe("processing schemas", () => {
  it("accepts upload responses with validation warnings", () => {
    const response = parseUploadResponse({
      job_id: "scene_abc123",
      validation_status: "warning",
      warnings: ["Low texture on one wall"],
      estimated_processing_time_sec: 240
    });

    expect(response.validation_status).toBe("warning");
  });

  it("accepts the scene-specific training progress stage", () => {
    const status = parseJobStatus({
      job_id: "scene_abc123",
      state: "running",
      stage: "training_scene_model",
      progress: 0.62,
      elapsed_sec: 148,
      message: "Training geometrically consistent scene-specific completion model",
      output_scene_id: null,
      error_message: null
    });

    expect(status.stage).toBe("training_scene_model");
    expect(status.state).toBe("running");
  });

  it("accepts the frame extraction stage", () => {
    const status = parseJobStatus({
      job_id: "scene_abc123",
      state: "running",
      stage: "extracting_video_frames",
      progress: 0.14,
      elapsed_sec: 22,
      message: "Extracting video frames",
      output_scene_id: null,
      error_message: null
    });

    expect(status.stage).toBe("extracting_video_frames");
  });

  it("rejects progress values above completion", () => {
    expect(() =>
      parseJobStatus({
        job_id: "scene_abc123",
        state: "running",
        stage: "training_scene_model",
        progress: 1.2,
        elapsed_sec: 148,
        message: "Training geometrically consistent scene-specific completion model",
        output_scene_id: null,
        error_message: null
      })
    ).toThrow();
  });

  it("accepts completed jobs with an output scene", () => {
    const status = parseJobStatus({
      job_id: "scene_abc123",
      state: "completed",
      stage: "completed",
      progress: 1,
      elapsed_sec: 240,
      message: "Explorer ready",
      output_scene_id: "warehouse_01",
      error_message: null
    });

    expect(status.output_scene_id).toBe("warehouse_01");
  });

  it("accepts structured failed job details", () => {
    const status = parseJobStatus({
      job_id: "scene_abc123",
      state: "failed",
      stage: "failed",
      progress: 0.14,
      elapsed_sec: 18,
      message: "Processing failed",
      output_scene_id: null,
      error_message: "Frame extraction produced no JPG frames.",
      failed_stage: "extracting_video_frames",
      failed_artifact: "frame_extraction_command.json"
    });

    expect(status.failed_stage).toBe("extracting_video_frames");
    expect(status.failed_artifact).toBe("frame_extraction_command.json");
  });

  it("accepts JSON job artifact payloads", () => {
    const artifact = parseJobArtifact({
      job_id: "scene_abc123",
      artifact_name: "frame_extraction_command.json",
      payload: {
        exit_code: 1,
        stderr: "ffmpeg failed"
      }
    });

    expect(artifact.payload.stderr).toBe("ffmpeg failed");
  });

  it("accepts completed job viewer bundles", () => {
    const bundle = parseJobSceneBundle({
      job_id: "scene_abc123",
      output_scene_id: "scene_abc123",
      assets: {
        scene_id: "scene_abc123",
        splat_url: "/jobs/scene_abc123/viewer-assets/splat.ply",
        metadata_url: "/jobs/scene_abc123/viewer-assets/metadata.json",
        visibility_manifest_url: "/jobs/scene_abc123/viewer-assets/visibility_manifest.json",
        completion_manifest_url: "/jobs/scene_abc123/viewer-assets/completion_manifest.json",
        quality_report_url: "/jobs/scene_abc123/viewer-assets/quality.json"
      },
      metadata: viewerMetadata,
      quality: viewerQuality,
      camera_path_artifact: "camera_path.json",
      camera_path: viewerCameraPath,
      visibility: viewerVisibility,
      completion: viewerCompletion,
      asset_status: {
        scene_id: "scene_abc123",
        splat_url: "/jobs/scene_abc123/viewer-assets/splat.ply",
        splat_available: false,
        viewer_render_mode: "placeholder",
        missing_assets: ["splat.ply"]
      }
    });

    expect(bundle.metadata.scene_id).toBe("scene_abc123");
    expect(bundle.asset_status.viewer_render_mode).toBe("placeholder");
  });
});

const viewerCameraPath = {
  scene_id: "scene_abc123",
  coordinate_system: "dreamnav_viewer_v1",
  intrinsics: {
    width: 1280,
    height: 720,
    fx: 910,
    fy: 910,
    cx: 640,
    cy: 360
  },
  poses: [
    {
      frame_index: 0,
      timestamp_sec: 0,
      position: [0, 1.55, 0],
      rotation_xyzw: [0, 0, 0, 1],
      fov_degrees: 60
    }
  ]
};

const viewerVisibility = {
  scene_id: "scene_abc123",
  method: "voxel_visibility_v1",
  observed_threshold: 3,
  partial_threshold: [1, 2],
  observed_ratio: 0.62,
  partial_ratio: 0.22,
  completion_candidate_ratio: 0.11,
  unknown_ratio: 0.05,
  cells: [
    {
      cell_id: "cell_observed_001",
      center: [0, 1, -0.5],
      size_meters: 0.5,
      visibility_count: 5,
      zone: "observed"
    }
  ]
};

const viewerCompletion = {
  scene_id: "scene_abc123",
  model_enabled: true,
  architecture: "pose_conditioned_encoder_decoder",
  quality_gate: "warning",
  heldout_psnr_median: 21.4,
  cache_strategy: "none",
  cached_predictions: []
};

const viewerQuality = {
  scene_id: "scene_abc123",
  pose_backend: "stub",
  frame_count: 1,
  visibility_threshold_observed: 3,
  splat_fps: 0,
  scene_model_training_sec: 184,
  heldout_psnr_median: 21.4,
  quality_gate: "warning",
  completion_latency_ms_p50: null,
  completion_latency_ms_p95: null,
  runtime_path: "placeholder",
  cached_completion: false
};

const viewerMetadata = {
  scene_id: "scene_abc123",
  title: "Processed walkthrough",
  input_video: "walkthrough.mp4",
  duration_sec: 0,
  frame_count: 1,
  pose_backend: "stub",
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
    fp16_latency_ms_p50: null,
    compiled_latency_ms_p50: null,
    tensorrt_latency_ms_p50: null,
    cached_output_latency_ms_p50: null
  },
  zones: {
    observed: "observed_zone.json",
    partial: "partial_zone.json",
    completion: "completion_zone.json",
    unknown: "unknown_zone.json"
  },
  quality: {
    capture_score: 0.92,
    sharpness_score: 0.79,
    parallax_score: 0.82,
    texture_score: 0.8,
    splat_fps: 0,
    processing_time_sec: 0
  },
  product_tools: {
    lens_modes: ["24mm", "35mm", "50mm", "85mm"],
    camera_markers_enabled: true,
    notes_enabled: false
  }
};
