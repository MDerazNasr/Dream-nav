import { z } from "zod";
import {
  nonNegativeNumberSchema,
  qualityGateSchema,
  sceneIdSchema
} from "./common.js";

const completionPolicySchema = z.enum(["enabled", "warning_overlay", "disabled"]);

export const qualityReportSchema = z.object({
  scene_id: sceneIdSchema,
  pose_backend: z.string().min(1),
  frame_count: z.number().int().min(0),
  visibility_threshold_observed: z.number().int().min(1),
  splat_fps: nonNegativeNumberSchema,
  scene_model_training_sec: nonNegativeNumberSchema,
  heldout_psnr_median: nonNegativeNumberSchema.nullable(),
  quality_gate: qualityGateSchema,
  completion_policy: completionPolicySchema.default("warning_overlay"),
  quality_gate_reason: z.string().min(1).default("Quality gate details unavailable."),
  warning_threshold_psnr: nonNegativeNumberSchema.default(20),
  pass_threshold_psnr: nonNegativeNumberSchema.default(22),
  completion_latency_ms_p50: nonNegativeNumberSchema.nullable(),
  completion_latency_ms_p95: nonNegativeNumberSchema.nullable(),
  runtime_path: z.string().min(1),
  cached_completion: z.boolean()
});

export type QualityReport = z.infer<typeof qualityReportSchema>;

export function parseQualityReport(input: unknown): QualityReport {
  return qualityReportSchema.parse(input);
}
