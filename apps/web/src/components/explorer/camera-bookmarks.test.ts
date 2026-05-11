import { beforeEach, describe, expect, it } from "vitest";
import {
  cameraBookmarkStorageKey,
  loadCameraBookmarks,
  saveCameraBookmarks,
  type CameraBookmark
} from "./camera-bookmarks";

describe("camera bookmark storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("saves and loads valid camera bookmarks", () => {
    const storage = window.localStorage;
    const bookmark: CameraBookmark = {
      createdAt: "2026-05-11T10:00:00.000Z",
      id: "bookmark-1",
      label: "Shot 1",
      pose: {
        fovDegrees: 73,
        lensMode: "24mm",
        pitch: 0.1,
        position: [1, 1.55, -2],
        yaw: 0.4
      }
    };

    saveCameraBookmarks("warehouse_01", storage, [bookmark]);

    expect(loadCameraBookmarks("warehouse_01", storage)).toEqual([bookmark]);
  });

  it("ignores invalid persisted bookmark data", () => {
    const storage = window.localStorage;
    storage.setItem(cameraBookmarkStorageKey("warehouse_01"), JSON.stringify([{ label: "Broken" }]));

    expect(loadCameraBookmarks("warehouse_01", storage)).toEqual([]);
  });
});
