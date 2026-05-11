import { z } from "zod";
import {
  assetPathSchema,
  nonNegativeNumberSchema,
  qualityGateSchema,
  sceneIdSchema
} from "./common.js";

const cachedPredictionSchema = z.object({
  prediction_id: z.string().min(1),
  camera_pose_index: z.number().int().min(0),
  rgb_asset: assetPathSchema,
  confidence_mask_asset: assetPathSchema.nullable(),
  nearest_view_asset: assetPathSchema.nullable(),
  nearest_view_camera_pose_index: z.number().int().min(0).nullable(),
  latency_ms_p50: nonNegativeNumberSchema.nullable()
});

export const completionManifestSchema = z.object({
  scene_id: sceneIdSchema,
  model_enabled: z.boolean(),
  architecture: z.string().min(1),
  quality_gate: qualityGateSchema,
  heldout_psnr_median: nonNegativeNumberSchema.nullable(),
  cache_strategy: z.enum(["none", "planned_path"]),
  cached_predictions: z.array(cachedPredictionSchema)
});

export type CompletionManifest = z.infer<typeof completionManifestSchema>;

export function parseCompletionManifest(input: unknown): CompletionManifest {
  return completionManifestSchema.parse(input);
}
