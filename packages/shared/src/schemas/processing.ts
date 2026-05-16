import { z } from "zod";
import { sceneAssetStatusSchema } from "./asset-status.js";
import { sceneAssetsSchema } from "./api-contracts.js";
import { cameraPathSchema } from "./camera-path.js";
import { completionManifestSchema } from "./completion-manifest.js";
import { qualityReportSchema } from "./quality-report.js";
import { sceneMetadataSchema } from "./scene-metadata.js";
import { visibilityManifestSchema } from "./visibility-manifest.js";

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

export const gaussianImportResponseSchema = z.object({
  job_id: z.string().min(1),
  source_file: z.string().min(1),
  import_format: z.string().min(1),
  previous_gaussian_count: z.number().min(0).nullable().default(null),
  previous_observed_ratio: z.number().min(0).max(1).nullable().default(null),
  previous_completion_candidate_ratio: z.number().min(0).max(1).nullable().default(null),
  previous_quality_gate: z.string().min(1).nullable().default(null),
  gaussian_count: z.number().min(0),
  file_size_bytes: z.number().min(0),
  observed_ratio: z.number().min(0).max(1),
  completion_candidate_ratio: z.number().min(0).max(1),
  quality_gate: z.string().min(1),
  viewer_render_mode: z.enum(["placeholder", "splat"]),
  featured_candidate: z.boolean(),
  validation_status: z.enum(["pass", "warning", "reject"]),
  blockers: z.array(z.string().min(1)),
  warnings: z.array(z.string().min(1))
});

export const remoteDenseSubmissionResponseSchema = z.object({
  job_id: z.string().min(1),
  provider_url: z.string().min(1),
  remote_job_id: z.string().min(1).nullable().default(null),
  submission_status: z.literal("submitted"),
  backend: z.string().min(1).nullable().default(null),
  bundle_file: z.string().min(1),
  bundle_size_bytes: z.number().min(0),
  frame_count: z.number().min(0),
  source_video: z.string().min(1),
  callback_url: z.string().min(1),
  callback_token_configured: z.boolean(),
  worker_capabilities: z.lazy(() => remoteDenseCapabilitiesSchema),
  warnings: z.array(z.string().min(1))
});

export const remoteDenseResultSummarySchema = z.object({
  job_id: z.string().min(1),
  remote_job_id: z.string().min(1).nullable().default(null),
  backend: z.string().min(1).nullable().default(null),
  source_file: z.string().min(1),
  validation_status: z.enum(["pass", "warning", "reject"]),
  gaussian_count: z.number().min(0)
});

export const remoteDenseJobStatusResponseSchema = z.object({
  job_id: z.string().min(1),
  remote_job_id: z.string().min(1).nullable().default(null),
  status: z.enum(["submitted", "running", "completed", "failed"]),
  backend: z.string().min(1).nullable().default(null),
  source_video: z.string().min(1).nullable().default(null),
  frame_count: z.number().min(0).nullable().default(null),
  warnings: z.array(z.string().min(1)),
  error: z.string().min(1).nullable().default(null)
});

export const remoteDenseCapabilitiesSchema = z.object({
  provider_url: z.string().min(1).nullable().default(null),
  configured: z.boolean(),
  callback_token_configured: z.boolean(),
  backend: z.string().min(1).nullable().default(null),
  dense_command: z.string().min(1).nullable().default(null),
  bundled_adapter_available: z.boolean(),
  colmap_command: z.string().min(1).nullable().default(null),
  colmap_dense_supported: z.boolean(),
  colmap_dense_reason: z.string().min(1).nullable().default(null),
  allow_mock_fallback: z.boolean(),
  retained_job_count: z.number().min(0),
  real_dense_ready: z.boolean(),
  submission_allowed: z.boolean(),
  missing_requirements: z.array(z.string().min(1)),
  warnings: z.array(z.string().min(1))
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
  assets: sceneAssetsSchema,
  metadata: sceneMetadataSchema,
  quality: qualityReportSchema,
  camera_path_artifact: z.string().min(1),
  camera_path: cameraPathSchema,
  visibility: visibilityManifestSchema,
  completion: completionManifestSchema,
  asset_status: sceneAssetStatusSchema,
  remote_dense_result: remoteDenseResultSummarySchema.nullable().default(null)
});

export type JobLifecycleState = z.infer<typeof jobLifecycleStateSchema>;

export type ProcessingStage = z.infer<typeof processingStageSchema>;

export type UploadResponse = z.infer<typeof uploadResponseSchema>;

export type GaussianImportResponse = z.infer<typeof gaussianImportResponseSchema>;

export type RemoteDenseSubmissionResponse = z.infer<typeof remoteDenseSubmissionResponseSchema>;

export type RemoteDenseResultSummary = z.infer<typeof remoteDenseResultSummarySchema>;

export type RemoteDenseJobStatusResponse = z.infer<typeof remoteDenseJobStatusResponseSchema>;

export type RemoteDenseCapabilities = z.infer<typeof remoteDenseCapabilitiesSchema>;

export type JobStatus = z.infer<typeof jobStatusSchema>;

export type JobArtifact = z.infer<typeof jobArtifactSchema>;

export type JobSceneBundle = z.infer<typeof jobSceneBundleSchema>;

export function parseUploadResponse(input: unknown): UploadResponse {
  return uploadResponseSchema.parse(input);
}

export function parseGaussianImportResponse(input: unknown): GaussianImportResponse {
  return gaussianImportResponseSchema.parse(input);
}

export function parseRemoteDenseSubmissionResponse(input: unknown): RemoteDenseSubmissionResponse {
  return remoteDenseSubmissionResponseSchema.parse(input);
}

export function parseRemoteDenseResultSummary(input: unknown): RemoteDenseResultSummary {
  return remoteDenseResultSummarySchema.parse(input);
}

export function parseRemoteDenseJobStatusResponse(input: unknown): RemoteDenseJobStatusResponse {
  return remoteDenseJobStatusResponseSchema.parse(input);
}

export function parseRemoteDenseCapabilities(input: unknown): RemoteDenseCapabilities {
  return remoteDenseCapabilitiesSchema.parse(input);
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
