import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExplorerShell } from "./ExplorerShell";
import type { SceneBundle } from "@dream-nav/scene-registry";

vi.mock("./SceneViewport", () => ({
  SceneViewport: () => <div data-testid="scene-viewport" />
}));

const sceneBundle: SceneBundle = {
  demoScene: {
    scene_id: "warehouse_01",
    title: "Warehouse Scout",
    thumbnail_url: "/thumbs/warehouse_01.jpg",
    description: "Textured industrial placeholder scene"
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
  visibility: {
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
  completion: {
    scene_id: "warehouse_01",
    model_enabled: true,
    architecture: "pose_conditioned_encoder_decoder",
    quality_gate: "warning",
    heldout_psnr_median: 21.4,
    cache_strategy: "planned_path",
    cached_predictions: []
  }
};

describe("ExplorerShell", () => {
  it("renders scene title, lens controls, minimap, and metrics", () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    expect(screen.getByRole("heading", { name: "Warehouse Scout" })).not.toBeNull();
    expect(screen.getByRole("button", { name: "24mm" })).not.toBeNull();
    expect(screen.getByLabelText("Camera path")).not.toBeNull();
    expect(screen.getByText("torch_fp16")).not.toBeNull();
  });

  it("toggles the confidence overlay button state", () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    const toggle = screen.getByRole("button", { name: "Toggle confidence overlay" });
    expect(toggle.getAttribute("data-active")).toBe("true");

    fireEvent.click(toggle);

    expect(toggle.getAttribute("data-active")).toBe("false");
  });

  it("tracks saved camera markers", () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    fireEvent.click(screen.getByRole("button", { name: "Save camera marker" }));

    expect(screen.getByLabelText("Saved markers").textContent).toContain("1");
  });
});
