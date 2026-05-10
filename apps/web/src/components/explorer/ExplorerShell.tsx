"use client";

import type { SceneBundle } from "@dream-nav/scene-registry";
import type { LensMode } from "@dream-nav/shared";
import { BookmarkPlus, Gauge, Layers, Video } from "lucide-react";
import { useState } from "react";
import { LensSelector } from "./LensSelector";
import { MetricsPanel } from "./MetricsPanel";
import { Minimap } from "./Minimap";
import { SceneViewport } from "./SceneViewport";

type ExplorerShellProps = {
  sceneBundle: SceneBundle;
};

export function ExplorerShell({ sceneBundle }: ExplorerShellProps) {
  const [overlayEnabled, setOverlayEnabled] = useState(true);
  const [selectedLens, setSelectedLens] = useState<LensMode>("35mm");
  const [markerCount, setMarkerCount] = useState(0);

  return (
    <main className="explorer">
      <SceneViewport
        cameraPath={sceneBundle.cameraPath}
        lensMode={selectedLens}
        overlayEnabled={overlayEnabled}
        visibility={sceneBundle.visibility}
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
        <Minimap cameraPath={sceneBundle.cameraPath} visibility={sceneBundle.visibility} />
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

        <MetricsPanel quality={sceneBundle.quality} />
      </aside>

      <div className="bottom-bar">
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
          aria-label="Save camera marker"
          className="icon-button"
          onClick={() => setMarkerCount((current) => current + 1)}
          title="Save camera marker"
          type="button"
        >
          <BookmarkPlus size={18} aria-hidden="true" />
        </button>
        <span className="badge" aria-label="Saved markers">
          <Gauge size={15} aria-hidden="true" /> {markerCount}
        </span>
      </div>
    </main>
  );
}
