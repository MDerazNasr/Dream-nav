import { describe, expect, it } from "vitest";
import { parseJobArtifact, parseJobStatus, parseUploadResponse } from "./processing.js";

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
});
