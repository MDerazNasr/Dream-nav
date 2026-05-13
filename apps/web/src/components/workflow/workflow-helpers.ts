import type { DemoReadiness, JobStatus } from "@dream-nav/shared";

import type { ProcessedJobSceneBundle, ViewerSceneBundle } from "../../lib/dreamnav-api";
import { resolveBrowserAssetDirectoryUrl } from "../../lib/dreamnav-api";

export type ProcessingStageItem = {
  stage: Exclude<JobStatus["stage"], "completed" | "failed">;
  label: string;
};

export const processingStages: ProcessingStageItem[] = [
  { stage: "checking_capture_quality", label: "Checking capture quality" },
  { stage: "extracting_video_frames", label: "Extracting video frames" },
  { stage: "estimating_camera_motion", label: "Estimating camera motion" },
  { stage: "building_gaussian_scene", label: "Building Gaussian scene" },
  { stage: "computing_visibility_support", label: "Computing visibility support" },
  { stage: "rendering_training_views", label: "Rendering training views" },
  { stage: "training_scene_model", label: "Training scene-specific model" },
  { stage: "evaluating_heldout_viewpoints", label: "Evaluating held-out viewpoints" },
  { stage: "applying_quality_gate", label: "Applying quality gate" },
  { stage: "preparing_explorer", label: "Preparing explorer" }
];

export function toProcessedViewerBundle(
  baseBundle: ViewerSceneBundle,
  jobSceneBundle: ProcessedJobSceneBundle
): ViewerSceneBundle {
  return {
    ...baseBundle,
    demoScene: {
      scene_id: jobSceneBundle.output_scene_id,
      title: jobSceneBundle.metadata.title,
      thumbnail_url: baseBundle.demoScene.thumbnail_url,
      description: "Processed walkthrough from your upload"
    },
    assets: jobSceneBundle.assets,
    metadata: jobSceneBundle.metadata,
    quality: jobSceneBundle.quality,
    cameraPath: jobSceneBundle.camera_path,
    visibility: jobSceneBundle.visibility,
    completion: jobSceneBundle.completion,
    completionAssetBaseUrl: resolveBrowserAssetDirectoryUrl(jobSceneBundle.assets.completion_manifest_url),
    remoteDenseResult: jobSceneBundle.remote_dense_result,
    readiness: buildProcessedReadiness(jobSceneBundle),
    assetStatus: jobSceneBundle.asset_status,
    zoneArtifacts: jobSceneBundle.zoneArtifacts
  };
}

export function buildProcessedReadiness(jobSceneBundle: ProcessedJobSceneBundle): DemoReadiness {
  const blockers = jobSceneBundle.quality.quality_gate === "fail" ? ["Quality gate failed."] : [];
  const warnings =
    jobSceneBundle.quality.quality_gate === "warning"
      ? ["Completion must stay labeled as lower confidence."]
      : [];

  if (!jobSceneBundle.quality.cached_completion || jobSceneBundle.completion.cached_predictions.length === 0) {
    warnings.push("Cached completion fallback assets unavailable.");
  }

  return {
    scene_id: jobSceneBundle.output_scene_id,
    locked_scene: false,
    required_assets_present: jobSceneBundle.asset_status.missing_assets.length === 0,
    fallback_assets_present: jobSceneBundle.completion.cached_predictions.length > 0,
    quality_gate: jobSceneBundle.quality.quality_gate,
    cached_completion: jobSceneBundle.quality.cached_completion,
    viewer_render_mode: jobSceneBundle.asset_status.viewer_render_mode,
    status: blockers.length > 0 ? "blocked" : warnings.length > 0 ? "degraded" : "ready",
    blockers,
    warnings
  };
}

export function formatReadinessStatus(status: DemoReadiness["status"]): string {
  if (status === "ready") {
    return "Ready";
  }

  if (status === "blocked") {
    return "Blocked";
  }

  return "Degraded";
}

export function getStageLabel(stage: JobStatus["failed_stage"]): string | null {
  return processingStages.find((stageItem) => stageItem.stage === stage)?.label ?? null;
}

export function getFailureGuidance(
  failedStage: JobStatus["failed_stage"],
  errorMessage: string | null | undefined
): { summary: string; nextStep: string } {
  const message = errorMessage?.toLowerCase() ?? "";

  if (failedStage === "checking_capture_quality" || message.includes("empty")) {
    return {
      summary: "The uploaded file did not contain usable video data.",
      nextStep: "Choose a non-empty MP4, MOV, or M4V walkthrough and start processing again."
    };
  }

  if (
    failedStage === "extracting_video_frames" ||
    message.includes("frame extraction") ||
    message.includes("ffmpeg") ||
    message.includes("jpeg")
  ) {
    return {
      summary: "DreamNav could not turn the walkthrough into usable image frames.",
      nextStep: "Try a shorter, standard phone video with steady motion and good lighting."
    };
  }

  if (failedStage === "estimating_camera_motion" || message.includes("colmap") || message.includes("pose")) {
    return {
      summary: "DreamNav could not recover the camera path for this walkthrough.",
      nextStep: "Try a slower walkthrough with more textured surfaces and less motion blur."
    };
  }

  return {
    summary: "DreamNav could not finish this processing job.",
    nextStep: "Choose another video or use the demo scene while this pipeline stage is being checked."
  };
}
