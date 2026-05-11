"use client";

import type { QualityReport } from "@dream-nav/shared";
import type { ViewerCameraPose } from "./viewer-camera";

type MetricsPanelProps = {
  cameraPose: ViewerCameraPose;
  quality: QualityReport;
};

export function MetricsPanel({ cameraPose, quality }: MetricsPanelProps) {
  const metrics = [
    ["Splat FPS", quality.splat_fps.toFixed(0)],
    ["PSNR", formatNullableMetric(quality.heldout_psnr_median, " dB")],
    ["Gate", quality.quality_gate],
    ["Runtime", quality.runtime_path],
    ["Pose", formatPose(cameraPose)],
    ["FOV", `${cameraPose.fovDegrees} deg`],
    ["P50", formatNullableMetric(quality.completion_latency_ms_p50, " ms")],
    ["P95", formatNullableMetric(quality.completion_latency_ms_p95, " ms")]
  ];

  return (
    <section className="panel" aria-label="Quality metrics">
      <div className="panel-header">
        <h2 className="panel-title">Metrics</h2>
      </div>
      <dl className="metrics-grid">
        {metrics.map(([label, value]) => (
          <div className="metric" key={label}>
            <dt className="metric-label">{label}</dt>
            <dd className="metric-value">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function formatNullableMetric(value: number | null, suffix: string): string {
  if (value === null) {
    return "TBD";
  }

  return `${value}${suffix}`;
}

function formatPose(cameraPose: ViewerCameraPose): string {
  return `${cameraPose.position[0].toFixed(1)}, ${cameraPose.position[2].toFixed(1)}`;
}
