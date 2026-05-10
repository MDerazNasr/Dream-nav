import { z } from "zod";
import { nonNegativeNumberSchema, sceneIdSchema } from "./common.js";

const vector3Schema = z.tuple([z.number(), z.number(), z.number()]);

const quaternionSchema = z.tuple([z.number(), z.number(), z.number(), z.number()]);

const cameraIntrinsicsSchema = z.object({
  width: z.number().int().min(1),
  height: z.number().int().min(1),
  fx: nonNegativeNumberSchema,
  fy: nonNegativeNumberSchema,
  cx: nonNegativeNumberSchema,
  cy: nonNegativeNumberSchema
});

const cameraPoseSchema = z.object({
  frame_index: z.number().int().min(0),
  timestamp_sec: nonNegativeNumberSchema,
  position: vector3Schema,
  rotation_xyzw: quaternionSchema,
  fov_degrees: z.number().min(1).max(179)
});

export const cameraPathSchema = z.object({
  scene_id: sceneIdSchema,
  coordinate_system: z.literal("dreamnav_viewer_v1"),
  intrinsics: cameraIntrinsicsSchema,
  poses: z.array(cameraPoseSchema).min(1)
});

export type CameraPath = z.infer<typeof cameraPathSchema>;

export function parseCameraPath(input: unknown): CameraPath {
  return cameraPathSchema.parse(input);
}
