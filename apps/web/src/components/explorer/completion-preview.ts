import type { CameraPath, CompletionManifest } from "@dream-nav/shared";
import type { ViewerCameraPose } from "./viewer-camera";

export type CachedCompletionMatch = {
  baselineUrl: string | null;
  distanceMeters: number;
  maskUrl: string | null;
  prediction: CompletionManifest["cached_predictions"][number];
  rgbUrl: string;
};

export function selectNearestCachedCompletion(
  completion: CompletionManifest,
  cameraPath: CameraPath,
  currentPose: ViewerCameraPose,
  assetBaseUrl: string
): CachedCompletionMatch | null {
  if (!completion.model_enabled || completion.quality_gate === "fail") {
    return null;
  }

  const candidates = completion.cached_predictions
    .map((prediction) => {
      const pose = cameraPath.poses[prediction.camera_pose_index];
      if (!pose) {
        return null;
      }

      return {
        baselineUrl: prediction.nearest_view_asset
          ? resolvePredictionAssetUrl(assetBaseUrl, prediction.nearest_view_asset)
          : null,
        distanceMeters: positionDistance(currentPose.position, pose.position),
        maskUrl: prediction.confidence_mask_asset
          ? resolvePredictionAssetUrl(assetBaseUrl, prediction.confidence_mask_asset)
          : null,
        prediction,
        rgbUrl: resolvePredictionAssetUrl(assetBaseUrl, prediction.rgb_asset)
      };
    })
    .filter((candidate): candidate is CachedCompletionMatch => candidate !== null);

  return candidates.sort((a, b) => a.distanceMeters - b.distanceMeters)[0] ?? null;
}

function resolvePredictionAssetUrl(assetBaseUrl: string, assetPath: string): string {
  if (assetBaseUrl.startsWith("/")) {
    return `${assetBaseUrl}${assetPath}`;
  }

  return new URL(assetPath, assetBaseUrl).toString();
}

export function formatCompletionCacheStatus(
  completion: CompletionManifest,
  match: CachedCompletionMatch | null
): string {
  if (completion.quality_gate === "fail") {
    return "Disabled";
  }

  if (!completion.model_enabled) {
    return "Off";
  }

  if (!match) {
    return "No cache";
  }

  return `${match.prediction.prediction_id} · ${match.distanceMeters.toFixed(1)} m`;
}

function positionDistance(a: readonly [number, number, number], b: readonly [number, number, number]): number {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  const dz = a[2] - b[2];
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}
