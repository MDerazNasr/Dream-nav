import { describe, expect, it } from "vitest";
import { parseJobStatus, parseUploadResponse } from "./processing.js";

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
      stage: "training_scene_model",
      progress: 0.62,
      elapsed_sec: 148,
      message: "Training geometrically consistent scene-specific completion model"
    });

    expect(status.stage).toBe("training_scene_model");
  });

  it("rejects progress values above completion", () => {
    expect(() =>
      parseJobStatus({
        job_id: "scene_abc123",
        stage: "training_scene_model",
        progress: 1.2,
        elapsed_sec: 148,
        message: "Training geometrically consistent scene-specific completion model"
      })
    ).toThrow();
  });
});
