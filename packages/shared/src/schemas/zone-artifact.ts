import { z } from "zod";
import { nonNegativeNumberSchema, ratioSchema, sceneIdSchema } from "./common.js";
import { visibilityZoneSchema } from "./visibility-manifest.js";

const vector3Schema = z.tuple([z.number(), z.number(), z.number()]);

const zoneCellSchema = z.object({
  cell_id: z.string().min(1),
  center: vector3Schema,
  size_meters: nonNegativeNumberSchema,
  visibility_count: z.number().int().min(0),
  zone: visibilityZoneSchema
});

const zoneBoundsSchema = z.object({
  min: vector3Schema,
  max: vector3Schema
});

export const zoneArtifactSchema = z.object({
  scene_id: sceneIdSchema,
  zone: visibilityZoneSchema,
  source_manifest: z.literal("visibility_manifest.json"),
  cell_count: z.number().int().min(0),
  coverage_ratio: ratioSchema,
  bounds: zoneBoundsSchema.nullable(),
  cells: z.array(zoneCellSchema)
});

export type ZoneArtifact = z.infer<typeof zoneArtifactSchema>;

export function parseZoneArtifact(input: unknown): ZoneArtifact {
  return zoneArtifactSchema.parse(input);
}
