import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const currentFilePath = fileURLToPath(import.meta.url);

export const DEFAULT_WORKSPACE_ROOT = resolve(dirname(currentFilePath), "../../..");

export function resolveDataRoot(workspaceRoot = DEFAULT_WORKSPACE_ROOT): string {
  return join(workspaceRoot, "data");
}

export function resolveSceneRoot(dataRoot: string, sceneId: string): string {
  return join(dataRoot, "scenes", sceneId);
}
