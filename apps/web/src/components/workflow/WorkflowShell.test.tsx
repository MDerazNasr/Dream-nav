import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WorkflowShell } from "./WorkflowShell";
import type { ViewerSceneBundle } from "../../lib/dreamnav-api";
import { fetchJobArtifact, fetchJobSceneBundle, fetchJobStatus } from "../../lib/dreamnav-api";

const processedCameraPath = vi.hoisted(() => ({
  scene_id: "warehouse_01",
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
      frame_index: 12,
      timestamp_sec: 0.4,
      position: [0.2, 1.55, -0.6],
      rotation_xyzw: [0, 0.03, 0, 0.9995],
      fov_degrees: 60
    }
  ]
}));

vi.mock("../explorer/ExplorerShell", () => ({
  ExplorerShell: ({ sceneBundle }: { sceneBundle: ViewerSceneBundle }) => (
    <div data-testid="explorer-shell">{sceneBundle.cameraPath.poses.length} poses</div>
  )
}));

vi.mock("../../lib/dreamnav-api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/dreamnav-api")>();

  return {
    ...actual,
    fetchJobStatus: vi.fn(async () => ({
      job_id: "scene_abc123",
      state: "running",
      stage: "training_scene_model",
      progress: 0.72,
      elapsed_sec: 148,
      message: "Training geometrically consistent scene-specific completion model",
      output_scene_id: null,
      error_message: null,
      failed_stage: null,
      failed_artifact: null
    })),
    fetchJobArtifact: vi.fn(async () => ({
      job_id: "scene_abc123",
      artifact_name: "frame_extraction_command.json",
      payload: {
        exit_code: 1,
        stderr: "ffmpeg failed"
      }
    })),
    fetchJobSceneBundle: vi.fn(async () => ({
      job_id: "scene_abc123",
      output_scene_id: "warehouse_01",
      camera_path_artifact: "camera_path.json",
      camera_path: processedCameraPath
    })),
    uploadWalkthrough: vi.fn(async () => ({
      job_id: "scene_abc123",
      validation_status: "pass",
      warnings: [],
      estimated_processing_time_sec: 240
    }))
  };
});

const sceneBundle = {
  demoScene: {
    scene_id: "warehouse_01",
    title: "Warehouse Scout",
    thumbnail_url: "/thumbs/warehouse_01.jpg",
    description: "Textured industrial space with partial corner completion"
  },
  assets: {
    scene_id: "warehouse_01",
    splat_url: "/scenes/warehouse_01/splat.ply",
    metadata_url: "/scenes/warehouse_01/metadata.json",
    visibility_manifest_url: "/scenes/warehouse_01/visibility_manifest.json",
    completion_manifest_url: "/scenes/warehouse_01/completion_manifest.json",
    quality_report_url: "/scenes/warehouse_01/quality.json"
  },
  metadata: {
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
  quality: {
    scene_id: "warehouse_01",
    pose_backend: "COLMAP",
    frame_count: 742,
    visibility_threshold_observed: 3,
    splat_fps: 42,
    scene_model_training_sec: 184,
    heldout_psnr_median: 21.4,
    quality_gate: "warning",
    completion_latency_ms_p50: 68,
    completion_latency_ms_p95: 91,
    runtime_path: "torch_fp16",
    cached_completion: true
  },
  cameraPath: {
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
    poses: []
  },
  visibility: {
    scene_id: "warehouse_01",
    method: "voxel_visibility_v1",
    observed_threshold: 3,
    partial_threshold: [1, 2],
    observed_ratio: 0.62,
    partial_ratio: 0.22,
    completion_candidate_ratio: 0.11,
    unknown_ratio: 0.05,
    cells: []
  },
  completion: {
    scene_id: "warehouse_01",
    model_enabled: true,
    architecture: "pose_conditioned_encoder_decoder",
    quality_gate: "warning",
    heldout_psnr_median: 21.4,
    cache_strategy: "planned_path",
    cached_predictions: []
  },
  assetStatus: {
    scene_id: "warehouse_01",
    splat_url: "http://api.test/scenes/warehouse_01/splat.ply",
    splat_available: true,
    viewer_render_mode: "splat",
    missing_assets: []
  }
} satisfies ViewerSceneBundle;

describe("WorkflowShell", () => {
  it("opens the prevalidated demo scene", () => {
    render(<WorkflowShell sceneBundle={sceneBundle} />);

    fireEvent.click(screen.getByRole("button", { name: "Open demo" }));

    expect(screen.getByTestId("explorer-shell")).not.toBeNull();
  });

  it("uploads a video and shows processing progress", async () => {
    render(<WorkflowShell sceneBundle={sceneBundle} />);
    const input = screen.getByLabelText("Walkthrough video");
    const file = new File(["video"], "walkthrough.mp4", { type: "video/mp4" });

    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Processing walkthrough" })).not.toBeNull();
    });
    await waitFor(() => {
      expect(screen.getByText("Training geometrically consistent scene-specific completion model")).not.toBeNull();
    });
    expect(screen.getByText("Extracting video frames")).not.toBeNull();
    expect(screen.getByRole("button", { name: "Open explorer" }).hasAttribute("disabled")).toBe(true);
  });

  it("enables explorer when the worker completes the job", async () => {
    vi.mocked(fetchJobStatus).mockResolvedValueOnce({
      job_id: "scene_abc123",
      state: "completed",
      stage: "completed",
      progress: 1,
      elapsed_sec: 240,
      message: "Explorer ready",
      output_scene_id: "warehouse_01",
      error_message: null,
      failed_stage: null,
      failed_artifact: null
    });
    render(<WorkflowShell sceneBundle={sceneBundle} />);
    const input = screen.getByLabelText("Walkthrough video");

    fireEvent.change(input, {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Open explorer" }).hasAttribute("disabled")).toBe(false);
    });
  });

  it("opens completed jobs with their generated camera path", async () => {
    vi.mocked(fetchJobStatus).mockResolvedValueOnce({
      job_id: "scene_abc123",
      state: "completed",
      stage: "completed",
      progress: 1,
      elapsed_sec: 240,
      message: "Explorer ready",
      output_scene_id: "warehouse_01",
      error_message: null,
      failed_stage: null,
      failed_artifact: null
    });
    render(<WorkflowShell sceneBundle={sceneBundle} />);

    fireEvent.change(screen.getByLabelText("Walkthrough video"), {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Open explorer" }).hasAttribute("disabled")).toBe(false);
    });
    fireEvent.click(screen.getByRole("button", { name: "Open explorer" }));

    await waitFor(() => {
      expect(screen.getByTestId("explorer-shell").textContent).toBe("2 poses");
    });
    expect(fetchJobSceneBundle).toHaveBeenCalledWith("scene_abc123");
  });

  it("shows failed job guidance and lets the user return to upload", async () => {
    vi.mocked(fetchJobStatus).mockResolvedValueOnce({
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
    render(<WorkflowShell sceneBundle={sceneBundle} />);
    const input = screen.getByLabelText("Walkthrough video");

    fireEvent.change(input, {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Processing stopped" })).not.toBeNull();
    });
    expect(screen.getByText("Failed while extracting video frames.")).not.toBeNull();
    expect(screen.getByText("Pipeline stage: Extracting video frames")).not.toBeNull();
    expect(screen.getByText("Frame extraction produced no JPG frames.")).not.toBeNull();
    expect(screen.getByText("Debug artifact: frame_extraction_command.json")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Choose another video" }));

    expect(screen.getByRole("button", { name: "Start processing" })).not.toBeNull();
  });

  it("loads debug artifacts from failed jobs", async () => {
    vi.mocked(fetchJobStatus).mockResolvedValueOnce({
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
    render(<WorkflowShell sceneBundle={sceneBundle} />);

    fireEvent.change(screen.getByLabelText("Walkthrough video"), {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "View debug artifact" })).not.toBeNull();
    });
    fireEvent.click(screen.getByRole("button", { name: "View debug artifact" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Debug artifact payload").textContent).toContain("ffmpeg failed");
    });
    expect(fetchJobArtifact).toHaveBeenCalledWith("scene_abc123", "frame_extraction_command.json");
  });
});
