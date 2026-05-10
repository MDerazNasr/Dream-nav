import { z } from "zod";

export const processingStageSchema = z.enum([
  "checking_capture_quality",
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

export const uploadResponseSchema = z.object({
  job_id: z.string().min(1),
  validation_status: z.enum(["pass", "warning", "fail"]),
  warnings: z.array(z.string()),
  estimated_processing_time_sec: z.number().min(0)
});

export const jobStatusSchema = z.object({
  job_id: z.string().min(1),
  stage: processingStageSchema,
  progress: z.number().min(0).max(1),
  elapsed_sec: z.number().min(0),
  message: z.string().min(1)
});

export type ProcessingStage = z.infer<typeof processingStageSchema>;

export type UploadResponse = z.infer<typeof uploadResponseSchema>;

export type JobStatus = z.infer<typeof jobStatusSchema>;

export function parseUploadResponse(input: unknown): UploadResponse {
  return uploadResponseSchema.parse(input);
}

export function parseJobStatus(input: unknown): JobStatus {
  return jobStatusSchema.parse(input);
}
