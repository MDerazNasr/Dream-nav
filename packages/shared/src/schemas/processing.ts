import { z } from "zod";
import { cameraPathSchema } from "./camera-path.js";

export const processingStageSchema = z.enum([
  "checking_capture_quality",
  "extracting_video_frames",
  "estimating_camera_motion",
  "building_gaussian_scene",
  "computing_visibility_support",
  "rendering_training_views",
  "training_scene_model",
  "evaluating_heldout_viewpoints",
  "applying_quality_gate",
  "preparing_explorer",
  "completed",
  "failed"
]);

export const jobLifecycleStateSchema = z.enum(["queued", "running", "completed", "failed"]);

export const uploadResponseSchema = z.object({
  job_id: z.string().min(1),
  validation_status: z.enum(["pass", "warning", "fail"]),
  warnings: z.array(z.string()),
  estimated_processing_time_sec: z.number().min(0)
});

export const jobStatusSchema = z.object({
  job_id: z.string().min(1),
  state: jobLifecycleStateSchema,
  stage: processingStageSchema,
  progress: z.number().min(0).max(1),
  elapsed_sec: z.number().min(0),
  message: z.string().min(1),
  output_scene_id: z.string().min(1).nullable(),
  error_message: z.string().min(1).nullable(),
  failed_stage: processingStageSchema.exclude(["completed", "failed"]).nullable().default(null),
  failed_artifact: z.string().min(1).nullable().default(null)
});

export const jobArtifactSchema = z.object({
  job_id: z.string().min(1),
  artifact_name: z.string().min(1),
  payload: z.record(z.string(), z.unknown())
});

export const jobSceneBundleSchema = z.object({
  job_id: z.string().min(1),
  output_scene_id: z.string().min(1),
  camera_path_artifact: z.string().min(1),
  camera_path: cameraPathSchema
});

export type JobLifecycleState = z.infer<typeof jobLifecycleStateSchema>;

export type ProcessingStage = z.infer<typeof processingStageSchema>;

export type UploadResponse = z.infer<typeof uploadResponseSchema>;

export type JobStatus = z.infer<typeof jobStatusSchema>;

export type JobArtifact = z.infer<typeof jobArtifactSchema>;

export type JobSceneBundle = z.infer<typeof jobSceneBundleSchema>;

export function parseUploadResponse(input: unknown): UploadResponse {
  return uploadResponseSchema.parse(input);
}

export function parseJobStatus(input: unknown): JobStatus {
  return jobStatusSchema.parse(input);
}

export function parseJobArtifact(input: unknown): JobArtifact {
  return jobArtifactSchema.parse(input);
}

export function parseJobSceneBundle(input: unknown): JobSceneBundle {
  return jobSceneBundleSchema.parse(input);
}
