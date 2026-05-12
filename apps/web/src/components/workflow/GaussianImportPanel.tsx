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
      setMessage(
        importSummary.featured_candidate
          ? "Imported asset passed the featured-scene gate."
          : "Imported asset loaded, but it does not pass the featured-scene gate yet."
      );
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
          <div className="import-review-grid">
            <article>
              <span>Gaussians</span>
              <strong>{gaussianSummary.gaussian_count.toLocaleString()}</strong>
            </article>
            <article>
              <span>Observed</span>
              <strong>{formatRatio(importedBundle.visibility.observed_ratio)}</strong>
            </article>
            <article>
              <span>Completion</span>
              <strong>{formatRatio(importedBundle.visibility.completion_candidate_ratio)}</strong>
            </article>
            <article>
              <span>Featured</span>
              <strong>{gaussianSummary.featured_candidate ? "Eligible" : "Not yet"}</strong>
            </article>
          </div>
          <small>
            Quality gate: {importedBundle.quality.quality_gate} · Render mode: {importedBundle.assetStatus.viewer_render_mode}
          </small>
        </section>
      ) : null}
      <div className="import-actions">
        <button className="secondary-action" disabled={isImporting} onClick={importDenseAsset} type="button">
          {isImporting ? "Importing dense asset" : "Import dense asset"}
        </button>
        <button
          className="primary-action"
          disabled={!importedBundle}
          onClick={() => importedBundle && onImported(importedBundle)}
          type="button"
        >
          Open imported scene
        </button>
      </div>
    </section>
  );
}

function formatRatio(value: number): string {
  return `${Math.round(value * 100)}%`;
}
