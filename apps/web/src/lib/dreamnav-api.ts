import type { SceneBundle } from "@dream-nav/scene-registry";
import {
  parseCameraPath,
  parseCompletionManifest,
  parseDemoScenesResponse,
  parseJobStatus,
  parseQualityReport,
  parseSceneAssetStatus,
  parseSceneAssets,
  parseSceneMetadata,
  parseUploadResponse,
  parseVisibilityManifest
} from "@dream-nav/shared";

import type { DemoScene, JobStatus, SceneAssetStatus, UploadResponse } from "@dream-nav/shared";

export type ViewerSceneBundle = SceneBundle & {
  assetStatus: SceneAssetStatus;
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

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

export async function fetchDemoScenes(
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<DemoScene[]> {
  return parseDemoScenesResponse(await fetchJson(apiBaseUrl, "/demo-scenes"));
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
    assetStatus: resolvedAssetStatus
  };
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

async function fetchJson(
  apiBaseUrl: string,
  path: string,
  init?: RequestInit
): Promise<unknown> {
  const response = await fetch(new URL(path, normalizeBaseUrl(apiBaseUrl)), {
    cache: "no-store",
    ...init
  });

  if (!response.ok) {
    throw new DreamNavApiError(`DreamNav API request failed for ${path}`, response.status);
  }

  return response.json() as Promise<unknown>;
}

function normalizeBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;
}
