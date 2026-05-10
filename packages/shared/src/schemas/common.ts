import { z } from "zod";

export const sceneIdSchema = z
  .string()
  .min(1)
  .regex(/^[a-z0-9]+(?:_[a-z0-9]+)*$/);

export const assetPathSchema = z
  .string()
  .min(1)
  .refine((value) => !value.includes(".."), "Asset paths must stay inside the scene root");

export const urlPathSchema = z.string().min(1).regex(/^\/[^\s]*$/);

export const ratioSchema = z.number().min(0).max(1);

export const nonNegativeNumberSchema = z.number().min(0);

export const qualityGateSchema = z.enum(["pass", "warning", "fail"]);

export const lensModeSchema = z.enum(["24mm", "35mm", "50mm", "85mm"]);

export type QualityGate = z.infer<typeof qualityGateSchema>;

export type LensMode = z.infer<typeof lensModeSchema>;
