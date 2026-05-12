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
      onImported(toProcessedViewerBundle(baseSceneBundle, jobSceneBundle));
      if (!importSummary.featured_candidate) {
        setMessage("Imported asset loaded, but it does not pass the featured-scene gate yet.");
      }
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
        onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
        type="file"
      />
      <span>{selectedFile?.name ?? "No file selected"}</span>
      {message ? <p className="workflow-error">{message}</p> : null}
      <div className="import-actions">
        <button className="secondary-action" disabled={isImporting} onClick={importDenseAsset} type="button">
          {isImporting ? "Importing dense asset" : "Import and open scene"}
        </button>
      </div>
    </section>
  );
}
