"use client";

import type { QualityGate, VisibilityManifest } from "@dream-nav/shared";
import {
  confidenceZoneColors,
  confidenceZoneLabels,
  confidenceZoneOrder,
  type ConfidenceZoneArtifacts
} from "../../lib/confidence-zones";

type ConfidenceLegendProps = {
  qualityGate: QualityGate;
  visibility: VisibilityManifest;
  zoneArtifacts: ConfidenceZoneArtifacts;
};

export function ConfidenceLegend({
  qualityGate,
  visibility,
  zoneArtifacts
}: ConfidenceLegendProps) {
  const showWarning = qualityGate !== "pass" || visibility.completion_candidate_ratio >= 0.35;

  return (
    <section className="panel confidence-panel" aria-label="Confidence zones">
      <div className="panel-header">
        <h2 className="panel-title">Confidence</h2>
      </div>
      <div className="confidence-list">
        {confidenceZoneOrder.map((zone) => (
          <div className="confidence-row" key={zone}>
            <span
              aria-hidden="true"
              className="zone-swatch"
              style={{ backgroundColor: confidenceZoneColors[zone] }}
            />
            <span>{confidenceZoneLabels[zone]}</span>
            <strong>{formatRatio(zoneArtifacts[zone].coverage_ratio)}</strong>
          </div>
        ))}
      </div>
      {showWarning ? (
        <p className="confidence-warning">Low-confidence completion is labeled before use.</p>
      ) : null}
    </section>
  );
}

function formatRatio(value: number): string {
  return `${Math.round(value * 100)}%`;
}
