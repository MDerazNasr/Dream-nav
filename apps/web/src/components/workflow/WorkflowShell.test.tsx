import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WorkflowShell } from "./WorkflowShell";
import { reconstructionCapabilities, sceneBundle } from "./WorkflowShell.fixtures";
import type { ViewerSceneBundle } from "../../lib/dreamnav-api";
import {
  fetchGaussianImportReview,
  fetchJobArtifact,
  fetchJobSceneBundle,
  fetchJobStatus,
  fetchRemoteDenseCapabilities,
  fetchRemoteDenseResultSummary,
  importGaussianAsset,
  submitRemoteDenseJob
} from "../../lib/dreamnav-api";

vi.mock("../explorer/ExplorerShell", () => ({
  ExplorerShell: ({ sceneBundle }: { sceneBundle: ViewerSceneBundle }) => (
    <div data-testid="explorer-shell">{sceneBundle.cameraPath.poses.length} poses</div>
  )
}));

vi.mock("../../lib/dreamnav-api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/dreamnav-api")>();
  const { processedJobSceneBundle } = await import("./WorkflowShell.fixtures");

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
    fetchJobSceneBundle: vi.fn(async () => processedJobSceneBundle),
    fetchGaussianImportReview: vi.fn(async () => null),
    fetchRemoteDenseCapabilities: vi.fn(async () => ({
      provider_url: "https://dense.example/jobs",
      configured: true,
      callback_token_configured: true,
      backend: "auto",
      dense_command: "/opt/dreamnav/dense-adapter",
      bundled_adapter_available: false,
      colmap_command: "/opt/homebrew/bin/colmap",
      colmap_dense_supported: true,
      colmap_dense_reason: null,
      allow_mock_fallback: true,
      retained_job_count: 8,
      real_dense_ready: true,
      submission_allowed: true,
      missing_requirements: [],
      warnings: []
    })),
    fetchRemoteDenseResultSummary: vi.fn(async () => null),
    importGaussianAsset: vi.fn(async () => ({
      job_id: "scene_abc123",
      source_file: "imports/dense_scene.ply",
      import_format: "point_cloud_ply",
      previous_gaussian_count: 6465,
      previous_observed_ratio: 0,
      previous_completion_candidate_ratio: 1,
      previous_quality_gate: "warning",
      gaussian_count: 24000,
      file_size_bytes: 128000,
      observed_ratio: 0.62,
      completion_candidate_ratio: 0.11,
      quality_gate: "warning",
      viewer_render_mode: "splat",
      featured_candidate: true,
      validation_status: "pass",
      blockers: [],
      warnings: []
    })),
    submitRemoteDenseJob: vi.fn(async () => ({
      job_id: "scene_abc123",
      provider_url: "https://dense.example/jobs",
      remote_job_id: "remote_001",
      submission_status: "submitted",
      backend: "colmap_dense",
      bundle_file: "remote_dense_bundle.zip",
      bundle_size_bytes: 180024,
      frame_count: 59,
      source_video: "walkthrough.mov",
      callback_url: "https://dreamnav.example/jobs/scene_abc123/remote-dense-result",
      callback_token_configured: true,
      worker_capabilities: {
        provider_url: "https://dense.example/jobs",
        configured: true,
        callback_token_configured: true,
        backend: "auto",
        dense_command: "/opt/dreamnav/dense-adapter",
        bundled_adapter_available: false,
        colmap_command: "/opt/homebrew/bin/colmap",
        colmap_dense_supported: true,
        colmap_dense_reason: null,
        allow_mock_fallback: true,
        retained_job_count: 8,
        real_dense_ready: true,
        submission_allowed: true,
        missing_requirements: [],
        warnings: []
      },
      warnings: []
    })),
    uploadWalkthrough: vi.fn(async () => ({
      job_id: "scene_abc123",
      validation_status: "pass",
      warnings: [],
      estimated_processing_time_sec: 240
    }))
  };
});

describe("WorkflowShell", () => {
  it("opens the prevalidated demo scene", () => {
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);

    expect(screen.getByLabelText("Demo readiness").textContent).toContain("Degraded");
    expect(screen.getByText("3DGS locked · Cached completion")).not.toBeNull();
    expect(screen.getByLabelText("Reconstruction pipeline").textContent).toContain("Partial pipeline");

    fireEvent.click(screen.getByRole("button", { name: "Open demo" }));

    expect(screen.getByTestId("explorer-shell")).not.toBeNull();
  });

  it("uploads a video and shows processing progress", async () => {
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);
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
    expect(screen.getByRole("button", { name: "Open processed scene" }).hasAttribute("disabled")).toBe(true);
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
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);
    const input = screen.getByLabelText("Walkthrough video");

    fireEvent.change(input, {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Open processed scene" }).hasAttribute("disabled")).toBe(false);
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
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);

    fireEvent.change(screen.getByLabelText("Walkthrough video"), {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Open processed scene" }).hasAttribute("disabled")).toBe(false);
    });
    fireEvent.click(screen.getByRole("button", { name: "Open processed scene" }));

    await waitFor(() => {
      expect(screen.getByTestId("explorer-shell").textContent).toBe("2 poses");
    });
    expect(fetchJobSceneBundle).toHaveBeenCalledWith("scene_abc123");
  });

  it("imports an external Gaussian asset for completed jobs", async () => {
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
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);

    fireEvent.change(screen.getByLabelText("Walkthrough video"), {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByLabelText("External Gaussian import")).not.toBeNull();
    });
    fireEvent.change(screen.getByLabelText("Gaussian asset"), {
      target: { files: [new File(["ply"], "dense_scene.ply", { type: "application/octet-stream" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Import dense asset" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Imported scene review").textContent).toContain("6,465 -> 24,000");
    });
    expect(screen.getByText("Approved")).not.toBeNull();
    expect(screen.getByText("Imported asset passed the review checks.")).not.toBeNull();
    expect(screen.getByText("0% -> 62%")).not.toBeNull();
    expect(screen.getByText("100% -> 11%")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Open imported scene" }));

    await waitFor(() => {
      expect(screen.getByTestId("explorer-shell").textContent).toBe("2 poses");
    });
    expect(importGaussianAsset).toHaveBeenCalledWith(
      "scene_abc123",
      expect.any(File)
    );
  });

  it("submits completed jobs to the remote dense backend", async () => {
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
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);

    fireEvent.change(screen.getByLabelText("Walkthrough video"), {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Remote dense backend")).not.toBeNull();
    });
    await waitFor(() => {
      expect(screen.getByLabelText("Remote dense readiness").textContent).toContain("Worker ready");
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit to remote dense backend" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Remote dense submission review").textContent).toContain("remote_001");
    });
    expect(screen.getByLabelText("Remote dense submission review").textContent).toContain("colmap_dense");
    expect(screen.getByText("Waiting for the remote worker to post the imported dense result back.")).not.toBeNull();
    expect(submitRemoteDenseJob).toHaveBeenCalledWith("scene_abc123");
    await waitFor(() => {
      expect(fetchGaussianImportReview).toHaveBeenCalledWith("scene_abc123");
      expect(fetchRemoteDenseResultSummary).toHaveBeenCalledWith("scene_abc123");
    });
  });

  it("blocks remote submission when the worker is not real-dense ready", async () => {
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
    vi.mocked(fetchRemoteDenseCapabilities).mockResolvedValueOnce({
      provider_url: "https://dense.example/jobs",
      configured: true,
      callback_token_configured: true,
      backend: "auto",
      dense_command: "/Users/mderaznasr/dreamnav/colmap_command_adapter.py",
      bundled_adapter_available: true,
      colmap_command: "/opt/homebrew/bin/colmap",
      colmap_dense_supported: false,
      colmap_dense_reason: "The configured COLMAP build does not support dense stereo.",
      allow_mock_fallback: true,
      retained_job_count: 8,
      real_dense_ready: false,
      submission_allowed: false,
      missing_requirements: ["Run the worker on a machine that can execute a real dense reconstruction backend."],
      warnings: ["The configured COLMAP build does not support dense stereo."]
    });
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);

    fireEvent.change(screen.getByLabelText("Walkthrough video"), {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Remote dense readiness").textContent).toContain("Worker blocked");
    });
    expect(screen.getByLabelText("Remote dense readiness").textContent).toContain(
      "Run the worker on a machine that can execute a real dense reconstruction backend."
    );
    expect(screen.getByRole("button", { name: "Submit to remote dense backend" }).hasAttribute("disabled")).toBe(true);
  });

  it("blocks opening rejected imported Gaussian assets", async () => {
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
    vi.mocked(importGaussianAsset).mockResolvedValueOnce({
      job_id: "scene_abc123",
      source_file: "imports/bad_dense_scene.ply",
      import_format: "point_cloud_ply",
      previous_gaussian_count: 24000,
      previous_observed_ratio: 0.62,
      previous_completion_candidate_ratio: 0.11,
      previous_quality_gate: "warning",
      gaussian_count: 1200,
      file_size_bytes: 64000,
      observed_ratio: 0.01,
      completion_candidate_ratio: 0.92,
      quality_gate: "warning",
      viewer_render_mode: "splat",
      featured_candidate: false,
      validation_status: "reject",
      blockers: ["Observed coverage is too low, which strongly suggests a bad alignment."],
      warnings: []
    });
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);

    fireEvent.change(screen.getByLabelText("Walkthrough video"), {
      target: { files: [new File(["video"], "walkthrough.mp4", { type: "video/mp4" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Start processing" }));

    await waitFor(() => {
      expect(screen.getByLabelText("External Gaussian import")).not.toBeNull();
    });
    fireEvent.change(screen.getByLabelText("Gaussian asset"), {
      target: { files: [new File(["ply"], "bad_dense_scene.ply", { type: "application/octet-stream" })] }
    });
    fireEvent.click(screen.getByRole("button", { name: "Import dense asset" }));

    await waitFor(() => {
      expect(screen.getByText("Rejected")).not.toBeNull();
    });
    expect(
      screen.getByText("Observed coverage is too low, which strongly suggests a bad alignment.")
    ).not.toBeNull();
    expect(screen.getByRole("button", { name: "Open imported scene" }).hasAttribute("disabled")).toBe(true);
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
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);
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
    render(<WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />);

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
