import { z } from "zod";
import {
  assetPathSchema,
  lensModeSchema,
  nonNegativeNumberSchema,
  qualityGateSchema,
  ratioSchema,
  sceneIdSchema
} from "./common.js";

const visibilitySchema = z.object({
  observed_threshold: z.number().int().min(1),
  partial_threshold: z.tuple([z.number().int().min(0), z.number().int().min(0)]),
  observed_ratio: ratioSchema,
  partial_ratio: ratioSchema,
  completion_candidate_ratio: ratioSchema
});

const sceneModelSchema = z.object({
  enabled: z.boolean(),
  architecture: z.string().min(1),
  train_views: z.number().int().min(0),
  heldout_views: z.number().int().min(0),
  training_time_sec: nonNegativeNumberSchema,
  loss: z.string().min(1),
  heldout_psnr_median: nonNegativeNumberSchema.nullable(),
  quality_gate: qualityGateSchema,
  lpips: nonNegativeNumberSchema.nullable()
});

const optimizationSchema = z.object({
  fp32_latency_ms_p50: nonNegativeNumberSchema.nullable(),
  fp16_latency_ms_p50: nonNegativeNumberSchema.nullable(),
  compiled_latency_ms_p50: nonNegativeNumberSchema.nullable(),
  tensorrt_latency_ms_p50: nonNegativeNumberSchema.nullable(),
  cached_output_latency_ms_p50: nonNegativeNumberSchema.nullable()
});

const zonesSchema = z.object({
  observed: assetPathSchema,
  partial: assetPathSchema,
  completion: assetPathSchema,
  unknown: assetPathSchema
});

const captureQualitySchema = z.object({
  capture_score: ratioSchema,
  sharpness_score: ratioSchema,
  parallax_score: ratioSchema,
  texture_score: ratioSchema,
  splat_fps: nonNegativeNumberSchema,
  processing_time_sec: nonNegativeNumberSchema
});

const productToolsSchema = z.object({
  lens_modes: z.array(lensModeSchema).min(1),
  camera_markers_enabled: z.boolean(),
  notes_enabled: z.boolean()
});

export const sceneMetadataSchema = z.object({
  scene_id: sceneIdSchema,
  title: z.string().min(1),
  input_video: assetPathSchema,
  duration_sec: nonNegativeNumberSchema,
  frame_count: z.number().int().min(0),
  pose_backend: z.string().min(1),
  camera_path: assetPathSchema,
  splat_file: assetPathSchema,
  visibility: visibilitySchema,
  scene_model: sceneModelSchema,
  optimization: optimizationSchema,
  zones: zonesSchema,
  quality: captureQualitySchema,
  product_tools: productToolsSchema
});

export type SceneMetadata = z.infer<typeof sceneMetadataSchema>;

export function parseSceneMetadata(input: unknown): SceneMetadata {
  return sceneMetadataSchema.parse(input);
}
