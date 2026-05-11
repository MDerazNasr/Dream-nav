"use client";

import type { LensMode } from "@dream-nav/shared";
import { BookmarkPlus, Gauge, Layers, RotateCcw, Trash2, Video } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ViewerSceneBundle } from "../../lib/dreamnav-api";
import {
  type CameraBookmark,
  getCameraBookmarkStorage,
  loadCameraBookmarks,
  saveCameraBookmarks
} from "./camera-bookmarks";
import {
  formatCompletionCacheStatus,
  selectNearestCachedCompletion
} from "./completion-preview";
import { CompletionPreview } from "./CompletionPreview";
import { ConfidenceLegend } from "./ConfidenceLegend";
import { LensSelector } from "./LensSelector";
import { MetricsPanel } from "./MetricsPanel";
import { Minimap } from "./Minimap";
import { SceneViewport } from "./SceneViewport";
import { initialViewerCameraPose, type ViewerCameraPose } from "./viewer-camera";

type ExplorerShellProps = {
  sceneBundle: ViewerSceneBundle;
};

export function ExplorerShell({ sceneBundle }: ExplorerShellProps) {
  const sceneId = sceneBundle.metadata.scene_id;
  const [overlayEnabled, setOverlayEnabled] = useState(true);
  const [selectedLens, setSelectedLens] = useState<LensMode>("35mm");
  const [currentPose, setCurrentPose] = useState<ViewerCameraPose>(() =>
    initialViewerCameraPose(sceneBundle.cameraPath, "35mm")
  );
  const [cameraBookmarks, setCameraBookmarks] = useState<CameraBookmark[]>([]);
  const [bookmarksSceneId, setBookmarksSceneId] = useState(sceneId);
  const [bookmarksLoaded, setBookmarksLoaded] = useState(false);
  const [restoreSignal, setRestoreSignal] = useState(0);
  const [restorePose, setRestorePose] = useState<ViewerCameraPose | null>(null);
  const [resetSignal, setResetSignal] = useState(0);
  const handleCameraPoseChange = useCallback((pose: ViewerCameraPose) => {
    setCurrentPose(pose);
  }, []);
  const cachedCompletionMatch = useMemo(
    () =>
      selectNearestCachedCompletion(
        sceneBundle.completion,
        sceneBundle.cameraPath,
        currentPose,
        sceneBundle.completionAssetBaseUrl
      ),
    [currentPose, sceneBundle.cameraPath, sceneBundle.completion, sceneBundle.completionAssetBaseUrl]
  );
  const completionCacheStatus = formatCompletionCacheStatus(sceneBundle.completion, cachedCompletionMatch);
  const completionProjection = useMemo(
    () =>
      cachedCompletionMatch
        ? {
            cameraPoseIndex: cachedCompletionMatch.prediction.camera_pose_index,
            maskUrl: cachedCompletionMatch.maskUrl,
            url: cachedCompletionMatch.rgbUrl
          }
        : null,
    [cachedCompletionMatch?.maskUrl, cachedCompletionMatch?.prediction.camera_pose_index, cachedCompletionMatch?.rgbUrl]
  );

  useEffect(() => {
    setBookmarksLoaded(false);
    setCameraBookmarks(loadCameraBookmarks(sceneId, getCameraBookmarkStorage()));
    setBookmarksSceneId(sceneId);
    setBookmarksLoaded(true);
  }, [sceneId]);

  useEffect(() => {
    if (bookmarksLoaded && bookmarksSceneId === sceneId) {
      saveCameraBookmarks(sceneId, getCameraBookmarkStorage(), cameraBookmarks);
    }
  }, [bookmarksLoaded, bookmarksSceneId, cameraBookmarks, sceneId]);

  const saveCurrentBookmark = () => {
    setCameraBookmarks((bookmarks) => [
      ...bookmarks,
      {
        createdAt: new Date().toISOString(),
        id: createBookmarkId(),
        label: `Shot ${bookmarks.length + 1}`,
        pose: currentPose
      }
    ]);
  };

  const restoreBookmark = (bookmark: CameraBookmark) => {
    setSelectedLens(bookmark.pose.lensMode);
    setCurrentPose(bookmark.pose);
    setRestorePose(bookmark.pose);
    setRestoreSignal((current) => current + 1);
  };

  const deleteBookmark = (bookmarkId: string) => {
    setCameraBookmarks((bookmarks) => bookmarks.filter((bookmark) => bookmark.id !== bookmarkId));
  };

  const resetCameraView = () => {
    setRestorePose(null);
    setResetSignal((current) => current + 1);
  };

  return (
    <main className="explorer">
      <SceneViewport
        cameraPath={sceneBundle.cameraPath}
        completionProjection={completionProjection}
        lensMode={selectedLens}
        onCameraPoseChange={handleCameraPoseChange}
        overlayEnabled={overlayEnabled}
        renderMode={sceneBundle.assetStatus.viewer_render_mode}
        restorePose={restorePose}
        restoreSignal={restoreSignal}
        resetSignal={resetSignal}
        splatUrl={sceneBundle.assetStatus.splat_url}
        zoneArtifacts={sceneBundle.zoneArtifacts}
      />

      <header className="top-bar">
        <span className="badge">
          <Video size={15} aria-hidden="true" />
        </span>
        <div>
          <h1 className="scene-title">{sceneBundle.metadata.title}</h1>
          <p className="scene-meta">
            {sceneBundle.metadata.pose_backend} · {sceneBundle.metadata.frame_count} frames
          </p>
        </div>
      </header>

      <aside className="left-panel panel" aria-label="Camera path minimap">
        <div className="panel-header">
          <h2 className="panel-title">Path</h2>
        </div>
        <Minimap
          cameraMarkers={cameraBookmarks.map((bookmark) => bookmark.pose)}
          cameraPath={sceneBundle.cameraPath}
          currentPose={currentPose}
          zoneArtifacts={sceneBundle.zoneArtifacts}
        />
      </aside>

      <aside className="right-panel">
        <section className="panel" aria-label="Lens preview">
          <div className="panel-header">
            <h2 className="panel-title">Lens</h2>
          </div>
          <LensSelector
            availableModes={sceneBundle.metadata.product_tools.lens_modes}
            selectedLens={selectedLens}
            onSelect={setSelectedLens}
          />
        </section>

        <MetricsPanel
          cameraPose={currentPose}
          completionCacheStatus={completionCacheStatus}
          quality={sceneBundle.quality}
        />

        <CompletionPreview completion={sceneBundle.completion} match={cachedCompletionMatch} />

        <ConfidenceLegend
          qualityGate={sceneBundle.quality.quality_gate}
          visibility={sceneBundle.visibility}
          zoneArtifacts={sceneBundle.zoneArtifacts}
        />

        <section className="panel" aria-label="Camera bookmarks">
          <div className="panel-header">
            <h2 className="panel-title">Bookmarks</h2>
            <span className="badge" aria-label="Camera bookmark count">
              {cameraBookmarks.length}
            </span>
          </div>
          <div className="bookmark-list">
            {cameraBookmarks.map((bookmark) => (
              <div className="bookmark-row" key={bookmark.id}>
                <button
                  className="bookmark-restore"
                  onClick={() => restoreBookmark(bookmark)}
                  type="button"
                >
                  <strong>{bookmark.label}</strong>
                  <span>
                    {bookmark.pose.lensMode} · {formatBookmarkPose(bookmark.pose)}
                  </span>
                </button>
                <button
                  aria-label={`Delete ${bookmark.label}`}
                  className="icon-button bookmark-delete"
                  onClick={() => deleteBookmark(bookmark.id)}
                  title={`Delete ${bookmark.label}`}
                  type="button"
                >
                  <Trash2 size={16} aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        </section>
      </aside>

      <div className="bottom-bar">
        <span className="badge" aria-label="Render mode">
          {sceneBundle.assetStatus.viewer_render_mode === "splat" ? "3DGS" : "Placeholder"}
        </span>
        <button
          aria-label="Toggle confidence overlay"
          className="icon-button"
          data-active={overlayEnabled}
          onClick={() => setOverlayEnabled((current) => !current)}
          title="Confidence overlay"
          type="button"
        >
          <Layers size={18} aria-hidden="true" />
        </button>
        <button
          aria-label="Reset camera view"
          className="icon-button"
          onClick={resetCameraView}
          title="Reset camera view"
          type="button"
        >
          <RotateCcw size={18} aria-hidden="true" />
        </button>
        <button
          aria-label="Save camera marker"
          className="icon-button"
          onClick={saveCurrentBookmark}
          title="Save camera marker"
          type="button"
        >
          <BookmarkPlus size={18} aria-hidden="true" />
        </button>
        <span className="badge" aria-label="Saved markers">
          <Gauge size={15} aria-hidden="true" /> {cameraBookmarks.length}
        </span>
      </div>
    </main>
  );
}

function formatBookmarkPose(pose: ViewerCameraPose): string {
  return `${pose.position[0].toFixed(1)}, ${pose.position[2].toFixed(1)}`;
}

function createBookmarkId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `bookmark-${Date.now()}`;
}
