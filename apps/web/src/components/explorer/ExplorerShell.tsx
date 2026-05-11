"use client";

import type { LensMode } from "@dream-nav/shared";
import { BookmarkPlus, Gauge, Layers, RotateCcw, Video } from "lucide-react";
import { useCallback, useState } from "react";
import type { ViewerSceneBundle } from "../../lib/dreamnav-api";
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
  const [overlayEnabled, setOverlayEnabled] = useState(true);
  const [selectedLens, setSelectedLens] = useState<LensMode>("35mm");
  const [currentPose, setCurrentPose] = useState<ViewerCameraPose>(() =>
    initialViewerCameraPose(sceneBundle.cameraPath, "35mm")
  );
  const [cameraMarkers, setCameraMarkers] = useState<ViewerCameraPose[]>([]);
  const [resetSignal, setResetSignal] = useState(0);
  const handleCameraPoseChange = useCallback((pose: ViewerCameraPose) => {
    setCurrentPose(pose);
  }, []);

  return (
    <main className="explorer">
      <SceneViewport
        cameraPath={sceneBundle.cameraPath}
        lensMode={selectedLens}
        onCameraPoseChange={handleCameraPoseChange}
        overlayEnabled={overlayEnabled}
        renderMode={sceneBundle.assetStatus.viewer_render_mode}
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
          cameraMarkers={cameraMarkers}
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

        <MetricsPanel cameraPose={currentPose} quality={sceneBundle.quality} />

        <ConfidenceLegend
          qualityGate={sceneBundle.quality.quality_gate}
          visibility={sceneBundle.visibility}
          zoneArtifacts={sceneBundle.zoneArtifacts}
        />
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
          onClick={() => setResetSignal((current) => current + 1)}
          title="Reset camera view"
          type="button"
        >
          <RotateCcw size={18} aria-hidden="true" />
        </button>
        <button
          aria-label="Save camera marker"
          className="icon-button"
          onClick={() => setCameraMarkers((markers) => [...markers, currentPose])}
          title="Save camera marker"
          type="button"
        >
          <BookmarkPlus size={18} aria-hidden="true" />
        </button>
        <span className="badge" aria-label="Saved markers">
          <Gauge size={15} aria-hidden="true" /> {cameraMarkers.length}
        </span>
      </div>
    </main>
  );
}
