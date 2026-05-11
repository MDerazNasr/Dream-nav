import type { ViewerCameraPose } from "./viewer-camera";

export type CameraBookmark = {
  createdAt: string;
  id: string;
  label: string;
  pose: ViewerCameraPose;
};

export function cameraBookmarkStorageKey(sceneId: string): string {
  return `dreamnav.camera-bookmarks.${sceneId}`;
}

export function getCameraBookmarkStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function loadCameraBookmarks(sceneId: string, storage: Storage | null): CameraBookmark[] {
  if (!storage) {
    return [];
  }

  const rawBookmarks = storage.getItem(cameraBookmarkStorageKey(sceneId));
  if (!rawBookmarks) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawBookmarks);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(isCameraBookmark);
  } catch {
    return [];
  }
}

export function saveCameraBookmarks(
  sceneId: string,
  storage: Storage | null,
  bookmarks: CameraBookmark[]
): void {
  if (!storage) {
    return;
  }

  try {
    storage.setItem(cameraBookmarkStorageKey(sceneId), JSON.stringify(bookmarks));
  } catch {
    return;
  }
}

function isCameraBookmark(value: unknown): value is CameraBookmark {
  if (!value || typeof value !== "object") {
    return false;
  }

  const bookmark = value as CameraBookmark;
  return (
    typeof bookmark.createdAt === "string" &&
    typeof bookmark.id === "string" &&
    typeof bookmark.label === "string" &&
    isViewerCameraPose(bookmark.pose)
  );
}

function isViewerCameraPose(value: unknown): value is ViewerCameraPose {
  if (!value || typeof value !== "object") {
    return false;
  }

  const pose = value as ViewerCameraPose;
  return (
    typeof pose.fovDegrees === "number" &&
    typeof pose.lensMode === "string" &&
    typeof pose.pitch === "number" &&
    Array.isArray(pose.position) &&
    pose.position.length === 3 &&
    pose.position.every((coordinate) => typeof coordinate === "number") &&
    typeof pose.yaw === "number"
  );
}
