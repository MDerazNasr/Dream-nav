import { z } from "zod";
import { sceneIdSchema, urlPathSchema } from "./common.js";

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

export type DemoScene = z.infer<typeof demoSceneSchema>;

export type SceneAssets = z.infer<typeof sceneAssetsSchema>;

export function parseDemoScenesResponse(input: unknown): DemoScene[] {
  return demoScenesResponseSchema.parse(input);
}

export function parseSceneAssets(input: unknown): SceneAssets {
  return sceneAssetsSchema.parse(input);
}
