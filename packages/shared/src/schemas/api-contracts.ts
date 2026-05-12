import { z } from "zod";
import { qualityGateSchema, sceneIdSchema, urlPathSchema } from "./common.js";

export const demoSceneSchema = z.object({
  scene_id: sceneIdSchema,
  title: z.string().min(1),
  thumbnail_url: urlPathSchema,
  description: z.string().min(1)
});

export const sceneAssetsSchema = z.object({
  scene_id: sceneIdSchema,
  splat_url: urlPathSchema,
  metadata_url: urlPathSchema,
  visibility_manifest_url: urlPathSchema,
  completion_manifest_url: urlPathSchema,
  quality_report_url: urlPathSchema
});

export const demoScenesResponseSchema = z.array(demoSceneSchema);

export const demoReadinessStatusSchema = z.enum(["ready", "degraded", "blocked"]);

export const reconstructionPipelineStatusSchema = z.enum(["stub", "mixed", "real"]);

export const demoReadinessSchema = z.object({
  scene_id: sceneIdSchema,
  locked_scene: z.boolean(),
  required_assets_present: z.boolean(),
  fallback_assets_present: z.boolean(),
  quality_gate: qualityGateSchema,
  cached_completion: z.boolean(),
  viewer_render_mode: z.enum(["placeholder", "splat"]),
  status: demoReadinessStatusSchema,
  blockers: z.array(z.string().min(1)),
  warnings: z.array(z.string().min(1))
});

export const reconstructionCapabilitiesSchema = z.object({
  frame_backend: z.string().min(1),
  pose_backend: z.string().min(1),
  gaussian_backend: z.string().min(1),
  frame_command: z.string().min(1).nullable(),
  pose_command: z.string().min(1).nullable(),
  gaussian_command: z.string().min(1).nullable(),
  pipeline_status: reconstructionPipelineStatusSchema,
  real_reconstruction_ready: z.boolean(),
  dense_reconstruction_ready: z.boolean(),
  dense_reconstruction_reason: z.string().min(1).nullable(),
  missing_requirements: z.array(z.string().min(1)),
  warnings: z.array(z.string().min(1))
});

export type DemoScene = z.infer<typeof demoSceneSchema>;

export type DemoReadiness = z.infer<typeof demoReadinessSchema>;

export type DemoReadinessStatus = z.infer<typeof demoReadinessStatusSchema>;

export type ReconstructionCapabilities = z.infer<typeof reconstructionCapabilitiesSchema>;

export type ReconstructionPipelineStatus = z.infer<typeof reconstructionPipelineStatusSchema>;

export type SceneAssets = z.infer<typeof sceneAssetsSchema>;

export function parseDemoScenesResponse(input: unknown): DemoScene[] {
  return demoScenesResponseSchema.parse(input);
}

export function parseSceneAssets(input: unknown): SceneAssets {
  return sceneAssetsSchema.parse(input);
}

export function parseDemoReadiness(input: unknown): DemoReadiness {
  return demoReadinessSchema.parse(input);
}

export function parseReconstructionCapabilities(input: unknown): ReconstructionCapabilities {
  return reconstructionCapabilitiesSchema.parse(input);
}
