"use client";

import type { CompletionManifest, QualityReport, SceneMetadata, VisibilityManifest } from "@dream-nav/shared";
import { Check, Copy } from "lucide-react";
import { useMemo, useState } from "react";
import type { CachedCompletionMatch } from "./completion-preview";
import type { ViewerCameraPose } from "./viewer-camera";

type QualityReportPanelProps = {
  completion: CompletionManifest;
  currentPose: ViewerCameraPose;
  match: CachedCompletionMatch | null;
  metadata: SceneMetadata;
  quality: QualityReport;
  visibility: VisibilityManifest;
};

type CopyStatus = "idle" | "copied" | "unavailable";

export function QualityReportPanel({
  completion,
  currentPose,
  match,
  metadata,
  quality,
  visibility
}: QualityReportPanelProps) {
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");
  const reportText = useMemo(
    () => buildQualityReportText({ completion, currentPose, match, metadata, quality, visibility }),
    [completion, currentPose, match, metadata, quality, visibility]
  );

  const handleCopyReport = async () => {
    try {
      await navigator.clipboard.writeText(reportText);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("unavailable");
    }
  };

  return (
    <section className="panel" aria-label="Quality report">
      <div className="panel-header">
        <h2 className="panel-title">Report</h2>
        <button className="report-copy" onClick={handleCopyReport} type="button">
          {copyStatus === "copied" ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
          {copyStatus === "copied" ? "Copied" : copyStatus === "unavailable" ? "Unavailable" : "Copy"}
        </button>
      </div>
      <dl className="report-grid">
        <div>
          <dt>Backend</dt>
          <dd>{quality.pose_backend}</dd>
        </div>
        <div>
          <dt>Frames</dt>
          <dd>{quality.frame_count}</dd>
        </div>
        <div>
          <dt>Cache</dt>
          <dd>{formatCacheStatus(completion.cache_status)}</dd>
        </div>
        <div>
          <dt>Lens</dt>
          <dd>{currentPose.lensMode}</dd>
        </div>
      </dl>
      <pre className="report-output" aria-label="Quality report text">
        {reportText}
      </pre>
    </section>
  );
}

export function buildQualityReportText({
  completion,
  currentPose,
  match,
  metadata,
  quality,
  visibility
}: QualityReportPanelProps): string {
  const prediction = match?.prediction;
  return [
    `DreamNav quality report: ${metadata.title}`,
    `Scene: ${metadata.scene_id}`,
    `Backend: ${quality.pose_backend}`,
    `Frames: ${quality.frame_count}`,
    `Held-out PSNR: ${formatNullableNumber(quality.heldout_psnr_median, " dB")}`,
    `Gate: ${quality.quality_gate}`,
    `Policy: ${quality.completion_policy}`,
    `Reason: ${quality.quality_gate_reason}`,
    `Runtime: ${quality.runtime_path}`,
    `Completion latency P50/P95: ${formatNullableNumber(quality.completion_latency_ms_p50, " ms")} / ${formatNullableNumber(quality.completion_latency_ms_p95, " ms")}`,
    `Cache: ${formatCacheStatus(completion.cache_status)}`,
    `Prediction: ${prediction?.prediction_id ?? "none"}`,
    `Prediction cache: ${prediction ? `${prediction.cache_status} · ${prediction.runtime_path}` : "none"}`,
    `Visibility observed/completion: ${formatRatio(visibility.observed_ratio)} / ${formatRatio(visibility.completion_candidate_ratio)}`,
    `Current lens/FOV: ${currentPose.lensMode} / ${currentPose.fovDegrees} deg`,
    `Current pose: ${currentPose.position[0].toFixed(1)}, ${currentPose.position[2].toFixed(1)}`
  ].join("\n");
}

function formatCacheStatus(status: CompletionManifest["cache_status"]): string {
  if (status === "ready") {
    return "Ready";
  }

  if (status === "disabled") {
    return "Disabled";
  }

  return "Empty";
}

function formatNullableNumber(value: number | null, suffix: string): string {
  return value === null ? "TBD" : `${value}${suffix}`;
}

function formatRatio(value: number): string {
  return `${Math.round(value * 100)}%`;
}
