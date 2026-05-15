import type { SceneBundle } from "@dream-nav/scene-registry";
import {
  parseCameraPath,
  parseCompletionManifest,
  parseDemoReadiness,
  parseDemoScenesResponse,
  parseGaussianImportResponse,
  parseJobArtifact,
  parseJobSceneBundle,
  parseJobStatus,
  parseRemoteDenseResultSummary,
  parseRemoteDenseCapabilities,
  parseQualityReport,
  parseReconstructionCapabilities,
  parseRemoteDenseSubmissionResponse,
  parseSceneAssetStatus,
  parseSceneAssets,
  parseSceneMetadata,
  parseUploadResponse,
  parseVisibilityManifest,
  parseZoneArtifact
} from "@dream-nav/shared";

import type {
  DemoReadiness,
  DemoScene,
  GaussianImportResponse,
  JobArtifact,
  JobSceneBundle,
  JobStatus,
  ReconstructionCapabilities,
  RemoteDenseResultSummary,
  RemoteDenseCapabilities,
  RemoteDenseSubmissionResponse,
  SceneAssetStatus,
  UploadResponse
} from "@dream-nav/shared";
import { buildZoneArtifactsFromVisibility, type ConfidenceZoneArtifacts } from "./confidence-zones";

export type ViewerSceneBundle = SceneBundle & {
  assetStatus: SceneAssetStatus;
  completionAssetBaseUrl: string;
  readiness: DemoReadiness;
  remoteDenseResult: RemoteDenseResultSummary | null;
  zoneArtifacts: ConfidenceZoneArtifacts;
};

export type ProcessedJobSceneBundle = JobSceneBundle & {
  zoneArtifacts: ConfidenceZoneArtifacts;
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const API_REQUEST_TIMEOUT_MS = 5000;

export class DreamNavApiError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
    this.name = "DreamNavApiError";
  }
}

export function getDreamNavApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_DREAMNAV_API_URL ?? process.env.DREAMNAV_API_URL ?? DEFAULT_API_BASE_URL;
}

export const fallbackReconstructionCapabilities: ReconstructionCapabilities = {
  frame_backend: "stub",
  pose_backend: "stub",
  gaussian_backend: "stub",
  frame_command: null,
  pose_command: null,
  gaussian_command: null,
  pipeline_status: "stub",
  real_reconstruction_ready: false,
  dense_reconstruction_ready: false,
  dense_reconstruction_reason: "Reconstruction status unavailable because the API did not respond.",
  missing_requirements: ["Restore the DreamNav API to inspect live reconstruction capability."],
  warnings: ["Showing fallback reconstruction status because the API is unavailable."]
};

export async function fetchDemoScenes(
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<DemoScene[]> {
  return parseDemoScenesResponse(await fetchJson(apiBaseUrl, "/demo-scenes"));
}

export async function fetchReconstructionCapabilities(
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<ReconstructionCapabilities> {
  return parseReconstructionCapabilities(await fetchJson(apiBaseUrl, "/reconstruction-capabilities"));
}

export async function fetchFeaturedSceneBundle(
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<ViewerSceneBundle> {
  const featuredJobSceneBundle = await fetchJobSceneBundleFromPath("/featured-job-scene-bundle", apiBaseUrl);
  return toViewerSceneBundleFromJob(featuredJobSceneBundle);
}

export async function fetchSceneBundle(
  sceneId: string,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<ViewerSceneBundle> {
  const demoScenes = await fetchDemoScenes(apiBaseUrl);
  const demoScene = demoScenes.find((scene) => scene.scene_id === sceneId);

  if (!demoScene) {
    throw new DreamNavApiError(`Scene ${sceneId} was not returned by /demo-scenes`, 404);
  }

  const assets = parseSceneAssets(await fetchJson(apiBaseUrl, `/scene/${sceneId}`));
  const metadata = parseSceneMetadata(await fetchJson(apiBaseUrl, assets.metadata_url));
  const quality = parseQualityReport(await fetchJson(apiBaseUrl, `/quality/${sceneId}`));
  const cameraPath = parseCameraPath(
    await fetchJson(apiBaseUrl, `/scenes/${sceneId}/${metadata.camera_path}`)
  );
  const visibility = parseVisibilityManifest(
    await fetchJson(apiBaseUrl, assets.visibility_manifest_url)
  );
  const completion = parseCompletionManifest(
    await fetchJson(apiBaseUrl, assets.completion_manifest_url)
  );
  const assetStatus = parseSceneAssetStatus(
    await fetchJson(apiBaseUrl, `/scene/${sceneId}/asset-status`)
  );
  const readiness = parseDemoReadiness(await fetchJson(apiBaseUrl, `/demo-readiness/${sceneId}`));
  const resolvedAssetStatus = {
    ...assetStatus,
    splat_url: new URL(assetStatus.splat_url, normalizeBaseUrl(apiBaseUrl)).toString()
  };

  return {
    demoScene,
    assets,
    metadata,
    quality,
    cameraPath,
    visibility,
    completion,
    completionAssetBaseUrl: resolveBrowserAssetDirectoryUrl(assets.completion_manifest_url),
    readiness,
    assetStatus: resolvedAssetStatus,
    remoteDenseResult: null,
    zoneArtifacts: buildZoneArtifactsFromVisibility(sceneId, visibility)
  };
}

export function resolveBrowserAssetDirectoryUrl(manifestUrl: string): string {
  const assetDirectory = new URL(".", new URL(manifestUrl, "http://dreamnav.local")).pathname;
  return `/dreamnav-assets${assetDirectory}`;
}

export async function uploadWalkthrough(
  file: File,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return parseUploadResponse(await fetchJson(apiBaseUrl, "/upload", {
    body: formData,
    method: "POST"
  }));
}

export async function fetchJobStatus(
  jobId: string,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<JobStatus> {
  return parseJobStatus(await fetchJson(apiBaseUrl, `/status/${jobId}`));
}

export async function fetchJobArtifact(
  jobId: string,
  artifactName: string,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<JobArtifact> {
  const encodedArtifactName = encodeURIComponent(artifactName);
  return parseJobArtifact(await fetchJson(apiBaseUrl, `/jobs/${jobId}/artifacts/${encodedArtifactName}`));
}

export async function fetchJobSceneBundle(
  jobId: string,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<ProcessedJobSceneBundle> {
  return fetchJobSceneBundleFromPath(`/jobs/${jobId}/scene-bundle`, apiBaseUrl);
}

export async function fetchGaussianImportReview(
  jobId: string,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<GaussianImportResponse | null> {
  try {
    const artifact = await fetchJobArtifact(jobId, "gaussian_import_review.json", apiBaseUrl);
    return parseGaussianImportResponse(artifact.payload);
  } catch (error) {
    if (error instanceof DreamNavApiError && error.status === 404) {
      return null;
    }

    throw error;
  }
}

export async function fetchRemoteDenseResultSummary(
  jobId: string,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<RemoteDenseResultSummary | null> {
  try {
    const artifact = await fetchJobArtifact(jobId, "remote_dense_result.json", apiBaseUrl);
    return parseRemoteDenseResultSummary(artifact.payload);
  } catch (error) {
    if (error instanceof DreamNavApiError && error.status === 404) {
      return null;
    }

    throw error;
  }
}

export async function fetchRemoteDenseCapabilities(
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<RemoteDenseCapabilities> {
  return parseRemoteDenseCapabilities(await fetchJson(apiBaseUrl, "/remote-dense-capabilities"));
}

export async function importGaussianAsset(
  jobId: string,
  file: File,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<GaussianImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return parseGaussianImportResponse(
    await fetchJson(apiBaseUrl, `/jobs/${jobId}/import-gaussian`, {
      body: formData,
      method: "POST"
    })
  );
}

export async function submitRemoteDenseJob(
  jobId: string,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<RemoteDenseSubmissionResponse> {
  return parseRemoteDenseSubmissionResponse(
    await fetchJson(apiBaseUrl, `/jobs/${jobId}/submit-remote-dense`, {
      method: "POST"
    })
  );
}

async function fetchJson(
  apiBaseUrl: string,
  path: string,
  init?: RequestInit
): Promise<unknown> {
  const timeoutSignal = AbortSignal.timeout(API_REQUEST_TIMEOUT_MS);
  const signal = init?.signal ? AbortSignal.any([init.signal, timeoutSignal]) : timeoutSignal;
  let response: Response;

  try {
    response = await fetch(new URL(path, normalizeBaseUrl(apiBaseUrl)), {
      cache: "no-store",
      ...init,
      signal
    });
  } catch (error) {
    if (timeoutSignal.aborted) {
      throw new DreamNavApiError(`DreamNav API request timed out for ${path}`, 504);
    }

    throw error;
  }

  if (!response.ok) {
    throw new DreamNavApiError(`DreamNav API request failed for ${path}`, response.status);
  }

  return response.json() as Promise<unknown>;
}

function normalizeBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;
}

async function fetchZoneArtifacts(
  apiBaseUrl: string,
  jobSceneBundle: JobSceneBundle
): Promise<ConfidenceZoneArtifacts> {
  const metadataUrl = new URL(jobSceneBundle.assets.metadata_url, normalizeBaseUrl(apiBaseUrl));
  const zoneEntries = await Promise.all(
    Object.entries(jobSceneBundle.metadata.zones).map(async ([zone, fileName]) => [
      zone,
      parseZoneArtifact(await fetchJson(apiBaseUrl, new URL(fileName, metadataUrl).toString()))
    ])
  );

  return Object.fromEntries(zoneEntries) as ConfidenceZoneArtifacts;
}

async function fetchJobSceneBundleFromPath(
  path: string,
  apiBaseUrl: string
): Promise<ProcessedJobSceneBundle> {
  const jobSceneBundle = parseJobSceneBundle(await fetchJson(apiBaseUrl, path));
  const zoneArtifacts = await fetchZoneArtifacts(apiBaseUrl, jobSceneBundle);
  return {
    ...jobSceneBundle,
    asset_status: {
      ...jobSceneBundle.asset_status,
      splat_url: new URL(jobSceneBundle.asset_status.splat_url, normalizeBaseUrl(apiBaseUrl)).toString()
    },
    zoneArtifacts
  };
}

function toViewerSceneBundleFromJob(jobSceneBundle: ProcessedJobSceneBundle): ViewerSceneBundle {
  return {
    demoScene: {
      scene_id: jobSceneBundle.output_scene_id,
      title: jobSceneBundle.metadata.title,
      thumbnail_url: "/thumbs/warehouse_01.jpg",
      description: "Latest generated reconstruction from local uploads"
    },
    assets: jobSceneBundle.assets,
    metadata: jobSceneBundle.metadata,
    quality: jobSceneBundle.quality,
    cameraPath: jobSceneBundle.camera_path,
    visibility: jobSceneBundle.visibility,
    completion: jobSceneBundle.completion,
    completionAssetBaseUrl: resolveBrowserAssetDirectoryUrl(jobSceneBundle.assets.completion_manifest_url),
    remoteDenseResult: jobSceneBundle.remote_dense_result,
    readiness: {
      scene_id: jobSceneBundle.output_scene_id,
      locked_scene: false,
      required_assets_present: jobSceneBundle.asset_status.missing_assets.length === 0,
      fallback_assets_present: jobSceneBundle.completion.cached_predictions.length > 0,
      quality_gate: jobSceneBundle.quality.quality_gate,
      cached_completion: jobSceneBundle.quality.cached_completion,
      viewer_render_mode: jobSceneBundle.asset_status.viewer_render_mode,
      status:
        jobSceneBundle.quality.quality_gate === "fail"
          ? "blocked"
          : jobSceneBundle.quality.quality_gate === "warning" ||
              jobSceneBundle.completion.cached_predictions.length === 0
            ? "degraded"
            : "ready",
      blockers: jobSceneBundle.quality.quality_gate === "fail" ? ["Quality gate failed."] : [],
      warnings: [
        ...(jobSceneBundle.quality.quality_gate === "warning"
          ? ["Completion must stay labeled as lower confidence."]
          : []),
        ...(jobSceneBundle.completion.cached_predictions.length === 0
          ? ["Cached completion fallback assets unavailable."]
          : [])
      ]
    },
    assetStatus: jobSceneBundle.asset_status,
    zoneArtifacts: jobSceneBundle.zoneArtifacts
  };
}
