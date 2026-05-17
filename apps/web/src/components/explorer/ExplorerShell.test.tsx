import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExplorerShell } from "./ExplorerShell";
import type { ViewerSceneBundle } from "../../lib/dreamnav-api";
import { buildZoneArtifactsFromVisibility } from "../../lib/confidence-zones";
import { cameraBookmarkStorageKey } from "./camera-bookmarks";

vi.mock("./SceneViewport", () => ({
  SceneViewport: ({
    completionProjection,
    onCameraPoseChange,
    resetSignal,
    restorePose,
    restoreSignal
  }: {
    completionProjection: { cameraPoseIndex: number; maskUrl: string | null; url: string } | null;
    onCameraPoseChange: (pose: {
      fovDegrees: number;
      lensMode: "24mm";
      pitch: number;
      position: [number, number, number];
      yaw: number;
    }) => void;
    resetSignal: number;
    restorePose: { position: [number, number, number] } | null;
    restoreSignal: number;
  }) => (
    <button
      data-testid="scene-viewport"
      onClick={() =>
        onCameraPoseChange({
          fovDegrees: 73,
          lensMode: "24mm",
          pitch: 0.2,
          position: [1.2, 1.55, -2.4],
          yaw: 0.6
        })
      }
      type="button"
    >
      projection:{completionProjection?.url ?? "none"};pose:{completionProjection?.cameraPoseIndex ?? "none"};
      mask:{completionProjection?.maskUrl ?? "none"};
      reset:{resetSignal};restore:{restoreSignal};x:{restorePose?.position[0] ?? "none"}
    </button>
  )
}));

const sceneVisibility: ViewerSceneBundle["visibility"] = {
  scene_id: "warehouse_01",
  method: "voxel_visibility_v1",
  observed_threshold: 3,
  partial_threshold: [1, 2],
  observed_ratio: 0.5,
  partial_ratio: 0.25,
  completion_candidate_ratio: 0.25,
  unknown_ratio: 0,
  cells: [
    {
      cell_id: "cell_observed_001",
      center: [0, 1, -0.5],
      size_meters: 0.5,
      visibility_count: 5,
      zone: "observed"
    },
    {
      cell_id: "cell_completion_001",
      center: [1, 1, -1],
      size_meters: 0.5,
      visibility_count: 0,
      zone: "completion"
    }
  ]
};

const sceneBundle: ViewerSceneBundle = {
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
    completion_policy: "warning_overlay",
    quality_gate_reason: "Held-out PSNR is below 22 dB but at least 20 dB.",
    warning_threshold_psnr: 20,
    pass_threshold_psnr: 22,
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
      },
      {
        frame_index: 24,
        timestamp_sec: 0.8,
        position: [1, 1.55, -2],
        rotation_xyzw: [0, 0.06, 0, 0.9982],
        fov_degrees: 60
      }
    ]
  },
  visibility: sceneVisibility,
  completion: {
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
        rgb_asset: "completion/pred_001.svg",
        confidence_mask_asset: "completion/pred_001_mask.svg",
        nearest_view_asset: "completion/baseline_nearest_001.png",
        nearest_view_camera_pose_index: 0,
        latency_ms_p50: 12,
        latency_ms_p95: 18,
        cache_key: "planned_path:warehouse_01:pose_0001:v1",
        cache_status: "hit",
        cache_source: "planned_path",
        cache_reason: "Cached during explorer preparation for the planned walkthrough path.",
        generated_at: "2026-05-12T00:00:00.000Z",
        runtime_path: "cached_output"
      }
    ]
  },
  completionAssetBaseUrl: "/dreamnav-assets/scenes/warehouse_01/",
  readiness: {
    scene_id: "warehouse_01",
    locked_scene: true,
    required_assets_present: true,
    fallback_assets_present: true,
    quality_gate: "warning",
    cached_completion: true,
    viewer_render_mode: "placeholder",
    status: "degraded",
    blockers: [],
    warnings: ["Completion must stay labeled as lower confidence."]
  },
  assetStatus: {
    scene_id: "warehouse_01",
    splat_url: "/scenes/warehouse_01/splat.ply",
    splat_available: false,
    viewer_render_mode: "placeholder",
    missing_assets: ["splat.ply"]
  },
  zoneArtifacts: buildZoneArtifactsFromVisibility("warehouse_01", sceneVisibility)
};

describe("ExplorerShell", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders scene title, lens controls, minimap, and metrics", () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    expect(screen.getByRole("heading", { name: "Warehouse Scout" })).not.toBeNull();
    expect(screen.getByRole("button", { name: "24mm" })).not.toBeNull();
    expect(screen.getByLabelText("Camera path")).not.toBeNull();
    expect(screen.getAllByText("torch_fp16").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Confidence zones")).not.toBeNull();
    expect(screen.getByText("Observed")).not.toBeNull();
    expect(screen.getAllByText("Completion").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Render mode").textContent).toContain("Placeholder");
    expect(screen.getByLabelText("Current camera position")).not.toBeNull();
    expect(screen.getByLabelText("Quality report")).not.toBeNull();
    expect(screen.getByLabelText("Quality report text").textContent).toContain("Warehouse Scout");
    expect(screen.getByLabelText("Quality report text").textContent).toContain("Current pose:");
    expect(screen.getByLabelText("Completion preview")).not.toBeNull();
    expect(screen.getByAltText("Cached completion prediction").getAttribute("src")).toBe(
      "/dreamnav-assets/scenes/warehouse_01/completion/pred_001.svg"
    );
    expect(screen.getByLabelText("Baseline comparison")).not.toBeNull();
    expect(screen.getByAltText("Model completion comparison").getAttribute("src")).toBe(
      "/dreamnav-assets/scenes/warehouse_01/completion/pred_001.svg"
    );
    expect(screen.getByAltText("Nearest-view baseline comparison").getAttribute("src")).toBe(
      "/dreamnav-assets/scenes/warehouse_01/completion/baseline_nearest_001.png"
    );
    expect(screen.getByText("Nearest view")).not.toBeNull();
    expect(screen.getByTestId("scene-viewport").textContent).toContain(
      "projection:/dreamnav-assets/scenes/warehouse_01/completion/pred_001.svg"
    );
    expect(screen.getByTestId("scene-viewport").textContent).toContain("pose:1");
    expect(screen.getByTestId("scene-viewport").textContent).toContain(
      "mask:/dreamnav-assets/scenes/warehouse_01/completion/pred_001_mask.svg"
    );
    expect(screen.getAllByText(/pred_001/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("12 ms").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Completion cache metadata")).not.toBeNull();
    expect(screen.getByText("Hit")).not.toBeNull();
    expect(screen.getByText("cached_output")).not.toBeNull();
    expect(screen.getByText("18 ms")).not.toBeNull();
    expect(screen.getByText("Planned path")).not.toBeNull();
  });

  it("toggles the confidence overlay button state", () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    const toggle = screen.getByRole("button", { name: "Toggle confidence overlay" });
    expect(toggle.getAttribute("data-active")).toBe("true");

    fireEvent.click(toggle);

    expect(toggle.getAttribute("data-active")).toBe("false");
  });

  it("starts with the confidence overlay disabled for splat scenes", () => {
    render(
      <ExplorerShell
        sceneBundle={{
          ...sceneBundle,
          assetStatus: {
            ...sceneBundle.assetStatus,
            viewer_render_mode: "splat",
            splat_available: true
          }
        }}
      />
    );

    expect(screen.getByRole("button", { name: "Toggle confidence overlay" }).getAttribute("data-active")).toBe(
      "false"
    );
  });

  it("tracks saved camera markers", async () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    fireEvent.click(screen.getByTestId("scene-viewport"));
    fireEvent.click(screen.getByRole("button", { name: "Save camera marker" }));

    expect(screen.getByLabelText("Saved markers").textContent).toContain("1");
    expect(screen.getByLabelText("Saved camera marker")).not.toBeNull();
    expect(screen.getByRole("button", { name: /^Shot 1/ })).not.toBeNull();
    await waitFor(() => {
      expect(window.localStorage.getItem(cameraBookmarkStorageKey("warehouse_01"))).toContain("Shot 1");
    });
  });

  it("updates the live camera pose from the viewport", () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    fireEvent.click(screen.getByTestId("scene-viewport"));

    expect(screen.getByText("1.2, -2.4")).not.toBeNull();
    expect(screen.getByText("73 deg")).not.toBeNull();
    expect(screen.getByText(/0.4 m/)).not.toBeNull();
  });

  it("resets the camera view", () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    fireEvent.click(screen.getByRole("button", { name: "Reset camera view" }));

    expect(screen.getByTestId("scene-viewport").textContent).toContain("reset:1");
  });

  it("restores and deletes camera bookmarks", () => {
    render(<ExplorerShell sceneBundle={sceneBundle} />);

    fireEvent.click(screen.getByTestId("scene-viewport"));
    fireEvent.click(screen.getByRole("button", { name: "Save camera marker" }));
    fireEvent.click(screen.getByRole("button", { name: /^Shot 1/ }));

    expect(screen.getByTestId("scene-viewport").textContent).toContain("restore:1");
    expect(screen.getByTestId("scene-viewport").textContent).toContain("x:1.2");

    fireEvent.click(screen.getByRole("button", { name: "Delete Shot 1" }));

    expect(screen.getByLabelText("Saved markers").textContent).toContain("0");
  });

  it("loads persisted camera bookmarks", async () => {
    window.localStorage.setItem(
      cameraBookmarkStorageKey("warehouse_01"),
      JSON.stringify([
        {
          createdAt: "2026-05-11T10:00:00.000Z",
          id: "bookmark-1",
          label: "Shot 1",
          pose: {
            fovDegrees: 73,
            lensMode: "24mm",
            pitch: 0.1,
            position: [2, 1.55, -3],
            yaw: 0.4
          }
        }
      ])
    );

    render(<ExplorerShell sceneBundle={sceneBundle} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^Shot 1/ })).not.toBeNull();
    });
    expect(screen.getByLabelText("Saved markers").textContent).toContain("1");
  });
});
