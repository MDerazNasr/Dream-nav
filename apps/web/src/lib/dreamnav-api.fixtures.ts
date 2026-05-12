export const jobSceneBundlePayload = {
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
  metadata: {
    scene_id: "scene_abc123",
    title: "Processed walkthrough",
    input_video: "walkthrough.mp4",
    duration_sec: 0,
    frame_count: 2,
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
  },
  quality: {
    scene_id: "scene_abc123",
    pose_backend: "stub",
    frame_count: 2,
    visibility_threshold_observed: 3,
    splat_fps: 0,
    scene_model_training_sec: 184,
    heldout_psnr_median: 21.4,
    quality_gate: "warning",
    completion_policy: "warning_overlay",
    quality_gate_reason: "Held-out PSNR is below 22 dB but at least 20 dB.",
    warning_threshold_psnr: 20,
    pass_threshold_psnr: 22,
    completion_latency_ms_p50: null,
    completion_latency_ms_p95: null,
    runtime_path: "placeholder",
    cached_completion: false
  },
  camera_path_artifact: "camera_path.json",
  camera_path: {
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
      },
      {
        frame_index: 8,
        timestamp_sec: 0.27,
        position: [0.1, 1.55, -0.4],
        rotation_xyzw: [0, 0.02, 0, 0.9998],
        fov_degrees: 60
      }
    ]
  },
  visibility: {
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
  },
  completion: {
    scene_id: "scene_abc123",
    model_enabled: true,
    architecture: "pose_conditioned_encoder_decoder",
    quality_gate: "warning",
    heldout_psnr_median: 21.4,
    cache_strategy: "none",
    cache_version: "completion_cache_v1",
    cache_status: "empty",
    cached_predictions: []
  },
  asset_status: {
    scene_id: "scene_abc123",
    splat_url: "/jobs/scene_abc123/viewer-assets/splat.ply",
    splat_available: false,
    viewer_render_mode: "placeholder",
    missing_assets: ["splat.ply"]
  }
};

export const jobZonePayloads = {
  "http://api.test/jobs/scene_abc123/viewer-assets/observed_zone.json": {
    scene_id: "scene_abc123",
    zone: "observed",
    source_manifest: "visibility_manifest.json",
    cell_count: 1,
    coverage_ratio: 1,
    bounds: {
      min: [0, 1, -0.5],
      max: [0, 1, -0.5]
    },
    cells: jobSceneBundlePayload.visibility.cells
  },
  "http://api.test/jobs/scene_abc123/viewer-assets/partial_zone.json": {
    scene_id: "scene_abc123",
    zone: "partial",
    source_manifest: "visibility_manifest.json",
    cell_count: 0,
    coverage_ratio: 0,
    bounds: null,
    cells: []
  },
  "http://api.test/jobs/scene_abc123/viewer-assets/completion_zone.json": {
    scene_id: "scene_abc123",
    zone: "completion",
    source_manifest: "visibility_manifest.json",
    cell_count: 0,
    coverage_ratio: 0,
    bounds: null,
    cells: []
  },
  "http://api.test/jobs/scene_abc123/viewer-assets/unknown_zone.json": {
    scene_id: "scene_abc123",
    zone: "unknown",
    source_manifest: "visibility_manifest.json",
    cell_count: 0,
    coverage_ratio: 0,
    bounds: null,
    cells: []
  }
};
