import { join } from "node:path";
import {
  type CameraPath,
  type CompletionManifest,
  type DemoScene,
  type QualityReport,
  type SceneAssets,
  type SceneMetadata,
  type VisibilityManifest,
  parseCameraPath,
  parseCompletionManifest,
  parseDemoScenesResponse,
  parseQualityReport,
  parseSceneMetadata,
  parseVisibilityManifest
} from "@dream-nav/shared";
import { readJsonFile } from "./json-file.js";
import { DEFAULT_WORKSPACE_ROOT, resolveDataRoot, resolveSceneRoot } from "./paths.js";

export type SceneBundle = {
  demoScene: DemoScene;
  assets: SceneAssets;
  metadata: SceneMetadata;
  quality: QualityReport;
  cameraPath: CameraPath;
  visibility: VisibilityManifest;
  completion: CompletionManifest;
};

export async function loadDemoScenes(workspaceRoot = DEFAULT_WORKSPACE_ROOT): Promise<DemoScene[]> {
  const registryPath = join(resolveDataRoot(workspaceRoot), "demo-scenes.json");
  return parseDemoScenesResponse(await readJsonFile(registryPath));
}

export function buildSceneAssets(sceneId: string): SceneAssets {
  return {
    scene_id: sceneId,
    splat_url: `/scenes/${sceneId}/splat.ply`,
    metadata_url: `/scenes/${sceneId}/metadata.json`,
    visibility_manifest_url: `/scenes/${sceneId}/visibility_manifest.json`,
    completion_manifest_url: `/scenes/${sceneId}/completion_manifest.json`,
    quality_report_url: `/scenes/${sceneId}/quality.json`
  };
}

export async function loadSceneBundle(
  sceneId: string,
  workspaceRoot = DEFAULT_WORKSPACE_ROOT
): Promise<SceneBundle> {
  const demoScene = await findDemoScene(sceneId, workspaceRoot);
  const sceneRoot = resolveSceneRoot(resolveDataRoot(workspaceRoot), sceneId);
  const metadata = parseSceneMetadata(await readJsonFile(join(sceneRoot, "metadata.json")));
  const quality = parseQualityReport(await readJsonFile(join(sceneRoot, "quality.json")));
  const cameraPath = parseCameraPath(await readJsonFile(join(sceneRoot, "camera_path.json")));
  const visibility = parseVisibilityManifest(
    await readJsonFile(join(sceneRoot, "visibility_manifest.json"))
  );
  const completion = parseCompletionManifest(
    await readJsonFile(join(sceneRoot, "completion_manifest.json"))
  );

  assertSceneIdsMatch(sceneId, metadata, quality, cameraPath, visibility, completion);

  return {
    demoScene,
    assets: buildSceneAssets(sceneId),
    metadata,
    quality,
    cameraPath,
    visibility,
    completion
  };
}

export async function loadAllSceneBundles(workspaceRoot = DEFAULT_WORKSPACE_ROOT): Promise<SceneBundle[]> {
  const demoScenes = await loadDemoScenes(workspaceRoot);
  return Promise.all(demoScenes.map((scene) => loadSceneBundle(scene.scene_id, workspaceRoot)));
}

async function findDemoScene(sceneId: string, workspaceRoot: string): Promise<DemoScene> {
  const demoScenes = await loadDemoScenes(workspaceRoot);
  const demoScene = demoScenes.find((scene) => scene.scene_id === sceneId);

  if (!demoScene) {
    throw new Error(`Unknown demo scene: ${sceneId}`);
  }

  return demoScene;
}

function assertSceneIdsMatch(
  sceneId: string,
  metadata: SceneMetadata,
  quality: QualityReport,
  cameraPath: CameraPath,
  visibility: VisibilityManifest,
  completion: CompletionManifest
): void {
  const manifestIds = [
    metadata.scene_id,
    quality.scene_id,
    cameraPath.scene_id,
    visibility.scene_id,
    completion.scene_id
  ];

  if (manifestIds.some((manifestId) => manifestId !== sceneId)) {
    throw new Error(`Scene manifest IDs do not match registry scene: ${sceneId}`);
  }
}
