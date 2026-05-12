"use client";

import { useState } from "react";

import type { ViewerSceneBundle } from "../../lib/dreamnav-api";
import { fetchJobSceneBundle, importGaussianAsset } from "../../lib/dreamnav-api";
import { toProcessedViewerBundle } from "./workflow-helpers";

type GaussianImportPanelProps = {
  baseSceneBundle: ViewerSceneBundle;
  jobId: string;
  onImported: (bundle: ViewerSceneBundle) => void;
};

export function GaussianImportPanel({ baseSceneBundle, jobId, onImported }: GaussianImportPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importedBundle, setImportedBundle] = useState<ViewerSceneBundle | null>(null);
  const [gaussianSummary, setGaussianSummary] = useState<Awaited<ReturnType<typeof importGaussianAsset>> | null>(null);

  const importDenseAsset = async () => {
    if (!selectedFile) {
      setMessage("Choose a .ply Gaussian asset first");
      return;
    }

    setIsImporting(true);
    setMessage(null);

    try {
      const importSummary = await importGaussianAsset(jobId, selectedFile);
      const jobSceneBundle = await fetchJobSceneBundle(jobId);
      const bundle = toProcessedViewerBundle(baseSceneBundle, jobSceneBundle);
      setGaussianSummary(importSummary);
      setImportedBundle(bundle);
      setMessage(null);
    } catch {
      setMessage("Dense asset import failed");
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <section className="upload-target gaussian-import-panel" aria-label="External Gaussian import">
      <span className="upload-title">External dense asset</span>
      <p className="import-copy">
        Replace the sparse reconstruction with a remote or prebuilt `.ply` scene for this completed job.
      </p>
      <label className="file-picker" htmlFor={`gaussian-import-${jobId}`}>
        Choose .ply
      </label>
      <input
        accept=".ply"
        aria-label="Gaussian asset"
        className="file-input"
        id={`gaussian-import-${jobId}`}
        onChange={(event) => {
          setSelectedFile(event.target.files?.[0] ?? null);
          setImportedBundle(null);
          setGaussianSummary(null);
        }}
        type="file"
      />
      <span>{selectedFile?.name ?? "No file selected"}</span>
      {message ? <p className="workflow-error">{message}</p> : null}
      {importedBundle && gaussianSummary ? (
        <section className="import-review" aria-label="Imported scene review">
          <div className="import-review-header">
            <span className="readiness-pill" data-status={reviewStatus(gaussianSummary.validation_status)}>
              {labelForValidation(gaussianSummary.validation_status)}
            </span>
            <small>
              {gaussianSummary.blockers[0] ??
                gaussianSummary.warnings[0] ??
                "Imported asset passed the review checks."}
            </small>
          </div>
          <div className="import-review-grid">
            <article>
              <span>Gaussians</span>
              <strong>{formatMetricPair(gaussianSummary.previous_gaussian_count, gaussianSummary.gaussian_count)}</strong>
            </article>
            <article>
              <span>Observed</span>
              <strong>{formatRatioPair(gaussianSummary.previous_observed_ratio, gaussianSummary.observed_ratio)}</strong>
            </article>
            <article>
              <span>Completion</span>
              <strong>
                {formatRatioPair(
                  gaussianSummary.previous_completion_candidate_ratio,
                  gaussianSummary.completion_candidate_ratio
                )}
              </strong>
            </article>
            <article>
              <span>Quality gate</span>
              <strong>{formatStringPair(gaussianSummary.previous_quality_gate, gaussianSummary.quality_gate)}</strong>
            </article>
            <article>
              <span>Featured</span>
              <strong>{gaussianSummary.featured_candidate ? "Eligible" : "Not yet"}</strong>
            </article>
          </div>
          <small>
            Render mode: {importedBundle.assetStatus.viewer_render_mode}
          </small>
        </section>
      ) : null}
      <div className="import-actions">
        <button className="secondary-action" disabled={isImporting} onClick={importDenseAsset} type="button">
          {isImporting ? "Importing dense asset" : "Import dense asset"}
        </button>
        <button
          className="primary-action"
          disabled={!importedBundle || gaussianSummary?.validation_status === "reject"}
          onClick={() => importedBundle && onImported(importedBundle)}
          type="button"
        >
          Open imported scene
        </button>
      </div>
    </section>
  );
}

function formatRatioPair(previous: number | null, current: number): string {
  return `${formatRatio(previous)} -> ${formatRatio(current)}`;
}

function formatMetricPair(previous: number | null, current: number): string {
  return `${previous?.toLocaleString() ?? "N/A"} -> ${current.toLocaleString()}`;
}

function formatStringPair(previous: string | null, current: string): string {
  return `${previous ?? "N/A"} -> ${current}`;
}

function formatRatio(value: number | null): string {
  if (typeof value !== "number") {
    return "N/A";
  }

  return `${Math.round(value * 100)}%`;
}

function labelForValidation(status: "pass" | "warning" | "reject"): string {
  if (status === "pass") {
    return "Approved";
  }

  if (status === "warning") {
    return "Needs review";
  }

  return "Rejected";
}

function reviewStatus(status: "pass" | "warning" | "reject"): "ready" | "degraded" | "blocked" {
  if (status === "pass") {
    return "ready";
  }

  if (status === "warning") {
    return "degraded";
  }

  return "blocked";
}
