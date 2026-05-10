import type { SceneBundle } from "@dream-nav/scene-registry";
import {
  parseCameraPath,
  parseCompletionManifest,
  parseDemoScenesResponse,
  parseQualityReport,
  parseSceneAssetStatus,
  parseSceneAssets,
  parseSceneMetadata,
  parseVisibilityManifest
} from "@dream-nav/shared";

import type { SceneAssetStatus } from "@dream-nav/shared";

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
  return process.env.DREAMNAV_API_URL ?? DEFAULT_API_BASE_URL;
}

export async function fetchSceneBundle(
  sceneId: string,
  apiBaseUrl = getDreamNavApiBaseUrl()
): Promise<ViewerSceneBundle> {
  const demoScenes = parseDemoScenesResponse(await fetchJson(apiBaseUrl, "/demo-scenes"));
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

  return {
    demoScene,
    assets,
    metadata,
    quality,
    cameraPath,
    visibility,
    completion,
    assetStatus
  };
}

async function fetchJson(apiBaseUrl: string, path: string): Promise<unknown> {
  const response = await fetch(new URL(path, normalizeBaseUrl(apiBaseUrl)), {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new DreamNavApiError(`DreamNav API request failed for ${path}`, response.status);
  }

  return response.json() as Promise<unknown>;
}

function normalizeBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;
}
