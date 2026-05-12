import { afterEach, describe, expect, it, vi } from "vitest";
import {
  DreamNavApiError,
  fetchFeaturedSceneBundle,
  importGaussianAsset,
  fetchReconstructionCapabilities,
  fetchJobArtifact,
  fetchJobSceneBundle,
  fetchJobStatus,
  fetchSceneBundle,
  getDreamNavApiBaseUrl,
  uploadWalkthrough
} from "./dreamnav-api";
import { jobSceneBundlePayload, jobZonePayloads } from "./dreamnav-api.fixtures";

const apiPayloads: Record<string, unknown> = {
  "http://api.test/demo-scenes": [
    {
      scene_id: "warehouse_01",
      title: "Warehouse Scout",
      thumbnail_url: "/thumbs/warehouse_01.jpg",
      description: "Textured industrial placeholder scene"
    }
  ],
  "http://api.test/scene/warehouse_01": {
    scene_id: "warehouse_01",
    splat_url: "/scenes/warehouse_01/splat.ply",
    metadata_url: "/scenes/warehouse_01/metadata.json",
    visibility_manifest_url: "/scenes/warehouse_01/visibility_manifest.json",
    completion_manifest_url: "/scenes/warehouse_01/completion_manifest.json",
    quality_report_url: "/scenes/warehouse_01/quality.json"
  },
  "http://api.test/scenes/warehouse_01/metadata.json": {
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
  },
  "http://api.test/quality/warehouse_01": {
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
  },
  "http://api.test/scenes/warehouse_01/camera_path.json": {
    scene_id: "warehouse_01",
    coordinate_system: "dreamnav_viewer_v1",
    intrinsics: {
      width: 1920,
      height: 1080,
      fx: 1240,
      fy: 1240,
      cx: 960,
      cy: 540
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
  },
  "http://api.test/scenes/warehouse_01/visibility_manifest.json": {
    scene_id: "warehouse_01",
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
  "http://api.test/scenes/warehouse_01/completion_manifest.json": {
    scene_id: "warehouse_01",
    model_enabled: true,
    architecture: "pose_conditioned_encoder_decoder",
    quality_gate: "warning",
    heldout_psnr_median: 21.4,
    cache_strategy: "planned_path",
    cache_version: "completion_cache_v1",
    cache_status: "empty",
    cached_predictions: []
  },
  "http://api.test/scene/warehouse_01/asset-status": {
    scene_id: "warehouse_01",
    splat_url: "/scenes/warehouse_01/splat.ply",
    splat_available: true,
    viewer_render_mode: "splat",
    missing_assets: []
  },
  "http://api.test/demo-readiness/warehouse_01": {
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
  },
  "http://api.test/reconstruction-capabilities": {
    frame_backend: "ffmpeg",
    pose_backend: "stub",
    gaussian_backend: "stub",
    frame_command: "/opt/homebrew/bin/ffmpeg",
    pose_command: null,
    gaussian_command: null,
    pipeline_status: "mixed",
    real_reconstruction_ready: false,
    dense_reconstruction_ready: false,
    dense_reconstruction_reason: "Dense reconstruction requires a COLMAP pose backend.",
    missing_requirements: [
      "Install COLMAP and set DREAMNAV_POSE_BACKEND=colmap.",
      "Set DREAMNAV_GAUSSIAN_BACKEND=command and DREAMNAV_GAUSSIAN_COMMAND to a real reconstruction wrapper."
    ],
    warnings: [
      "The current pipeline still falls back to placeholder geometry.",
      "Dense reconstruction requires a COLMAP pose backend."
    ]
  },
  "http://api.test/jobs/scene_abc123/import-gaussian": {
    job_id: "scene_abc123",
    source_file: "imports/dense_scene.ply",
    import_format: "point_cloud_ply",
    gaussian_count: 24000,
    file_size_bytes: 128000,
    viewer_render_mode: "splat",
    featured_candidate: true
  }
};

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("DreamNav API client", () => {
  it("uses the local API URL by default", () => {
    expect(getDreamNavApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("loads a complete scene bundle through HTTP contracts", async () => {
    mockFetchFromPayloads(apiPayloads);

    const bundle = await fetchSceneBundle("warehouse_01", "http://api.test");

    expect(bundle.metadata.title).toBe("Warehouse Scout");
    expect(bundle.quality.runtime_path).toBe("torch_fp16");
    expect(bundle.cameraPath.poses).toHaveLength(1);
    expect(bundle.assetStatus.viewer_render_mode).toBe("splat");
    expect(bundle.assetStatus.splat_url).toBe("http://api.test/scenes/warehouse_01/splat.ply");
    expect(bundle.readiness.status).toBe("degraded");
    expect(bundle.zoneArtifacts.observed.cell_count).toBe(1);
  });

  it("loads reconstruction capability summaries", async () => {
    mockFetchFromPayloads(apiPayloads);

    const capabilities = await fetchReconstructionCapabilities("http://api.test");

    expect(capabilities.pipeline_status).toBe("mixed");
    expect(capabilities.frame_command).toBe("/opt/homebrew/bin/ffmpeg");
  });

  it("throws a typed error when an API request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("missing", { status: 404 }))
    );

    await expect(fetchSceneBundle("warehouse_01", "http://api.test")).rejects.toMatchObject({
      name: "DreamNavApiError",
      status: 404
    } satisfies Partial<DreamNavApiError>);
  });

  it("throws a typed error when the scene is absent from the registry", async () => {
    mockFetchFromPayloads({
      "http://api.test/demo-scenes": []
    });

    await expect(fetchSceneBundle("warehouse_01", "http://api.test")).rejects.toMatchObject({
      status: 404
    });
  });

  it("uploads walkthrough videos through the processing contract", async () => {
    const fetchMock = vi.fn(async () =>
      Response.json({
        job_id: "scene_abc123",
        validation_status: "pass",
        warnings: [],
        estimated_processing_time_sec: 240
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await uploadWalkthrough(
      new File(["video"], "walkthrough.mp4", { type: "video/mp4" }),
      "http://api.test"
    );

    expect(response.job_id).toBe("scene_abc123");
    expect(fetchMock).toHaveBeenCalledWith(
      new URL("http://api.test/upload"),
      expect.objectContaining({
        body: expect.any(FormData),
        method: "POST"
      })
    );
  });

  it("imports external Gaussian assets for completed jobs", async () => {
    const fetchMock = vi.fn(async () =>
      Response.json(apiPayloads["http://api.test/jobs/scene_abc123/import-gaussian"])
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await importGaussianAsset(
      "scene_abc123",
      new File(["ply"], "dense_scene.ply", { type: "application/octet-stream" }),
      "http://api.test"
    );

    expect(response.import_format).toBe("point_cloud_ply");
    expect(fetchMock).toHaveBeenCalledWith(
      new URL("http://api.test/jobs/scene_abc123/import-gaussian"),
      expect.objectContaining({
        body: expect.any(FormData),
        method: "POST"
      })
    );
  });

  it("loads processing job status", async () => {
    mockFetchFromPayloads({
      "http://api.test/status/scene_abc123": {
        job_id: "scene_abc123",
        state: "running",
        stage: "training_scene_model",
        progress: 0.62,
        elapsed_sec: 148,
        message: "Training geometrically consistent scene-specific completion model",
        output_scene_id: null,
        error_message: null
      }
    });

    const response = await fetchJobStatus("scene_abc123", "http://api.test");

    expect(response.stage).toBe("training_scene_model");
  });

  it("loads job artifact payloads", async () => {
    mockFetchFromPayloads({
      "http://api.test/jobs/scene_abc123/artifacts/frame_extraction_command.json": {
        job_id: "scene_abc123",
        artifact_name: "frame_extraction_command.json",
        payload: {
          exit_code: 1,
          stderr: "ffmpeg failed"
        }
      }
    });

    const response = await fetchJobArtifact(
      "scene_abc123",
      "frame_extraction_command.json",
      "http://api.test"
    );

    expect(response.payload.stderr).toBe("ffmpeg failed");
  });

  it("loads completed job scene bundles", async () => {
    mockFetchFromPayloads({
      "http://api.test/jobs/scene_abc123/scene-bundle": jobSceneBundlePayload,
      ...jobZonePayloads
    });

    const response = await fetchJobSceneBundle("scene_abc123", "http://api.test");

    expect(response.output_scene_id).toBe("scene_abc123");
    expect(response.camera_path.poses).toHaveLength(2);
    expect(response.asset_status.splat_url).toBe("http://api.test/jobs/scene_abc123/viewer-assets/splat.ply");
    expect(response.zoneArtifacts.completion.zone).toBe("completion");
  });

  it("loads the featured completed scene bundle", async () => {
    mockFetchFromPayloads({
      "http://api.test/featured-job-scene-bundle": jobSceneBundlePayload,
      ...jobZonePayloads
    });

    const response = await fetchFeaturedSceneBundle("http://api.test");

    expect(response.demoScene.description).toBe("Latest generated reconstruction from local uploads");
    expect(response.assetStatus.splat_url).toBe("http://api.test/jobs/scene_abc123/viewer-assets/splat.ply");
    expect(response.metadata.scene_id).toBe("scene_abc123");
  });
});

function mockFetchFromPayloads(payloads: Record<string, unknown>): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: URL | RequestInfo) => {
      const url = input instanceof URL ? input.toString() : input.toString();
      const payload = payloads[url];

      if (!payload) {
        return new Response("missing", { status: 404 });
      }

      return Response.json(payload);
    })
  );
}
