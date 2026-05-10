import { z } from "zod";
import { sceneIdSchema, urlPathSchema } from "./common.js";

export const viewerRenderModeSchema = z.enum(["placeholder", "splat"]);

export const sceneAssetStatusSchema = z.object({
  scene_id: sceneIdSchema,
  splat_url: urlPathSchema,
  splat_available: z.boolean(),
  viewer_render_mode: viewerRenderModeSchema,
  missing_assets: z.array(z.string().min(1))
});

export type ViewerRenderMode = z.infer<typeof viewerRenderModeSchema>;

export type SceneAssetStatus = z.infer<typeof sceneAssetStatusSchema>;

export function parseSceneAssetStatus(input: unknown): SceneAssetStatus {
  return sceneAssetStatusSchema.parse(input);
}
