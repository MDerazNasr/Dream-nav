import { z } from "zod";
import { nonNegativeNumberSchema, ratioSchema, sceneIdSchema } from "./common.js";

const vector3Schema = z.tuple([z.number(), z.number(), z.number()]);

export const visibilityZoneSchema = z.enum([
  "observed",
  "partial",
  "completion",
  "unknown"
]);

const visibilityCellSchema = z.object({
  cell_id: z.string().min(1),
  center: vector3Schema,
  size_meters: nonNegativeNumberSchema,
  visibility_count: z.number().int().min(0),
  zone: visibilityZoneSchema
});

export const visibilityManifestSchema = z.object({
  scene_id: sceneIdSchema,
  method: z.enum(["voxel_visibility_v1", "voxel_visibility_v1_adaptive", "per_gaussian_visibility_v1"]),
  observed_threshold: z.number().int().min(1),
  partial_threshold: z.tuple([z.number().int().min(0), z.number().int().min(0)]),
  observed_ratio: ratioSchema,
  partial_ratio: ratioSchema,
  completion_candidate_ratio: ratioSchema,
  unknown_ratio: ratioSchema,
  adaptive_thresholds: z
    .object({
      near_radius_meters: nonNegativeNumberSchema,
      far_radius_meters: nonNegativeNumberSchema
    })
    .optional(),
  cells: z.array(visibilityCellSchema).min(1)
});

export type VisibilityZone = z.infer<typeof visibilityZoneSchema>;

export type VisibilityManifest = z.infer<typeof visibilityManifestSchema>;

export function parseVisibilityManifest(input: unknown): VisibilityManifest {
  return visibilityManifestSchema.parse(input);
}
