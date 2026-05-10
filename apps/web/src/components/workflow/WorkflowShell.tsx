"use client";

import type { JobStatus, UploadResponse } from "@dream-nav/shared";
import { CheckCircle2, Film, LoaderCircle, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ExplorerShell } from "../explorer/ExplorerShell";
import type { ViewerSceneBundle } from "../../lib/dreamnav-api";
import { fetchJobStatus, uploadWalkthrough } from "../../lib/dreamnav-api";

type WorkflowShellProps = {
  sceneBundle: ViewerSceneBundle;
};

const processingStages = [
  "Checking capture quality",
  "Estimating camera motion",
  "Building Gaussian scene",
  "Computing visibility support",
  "Rendering training views",
  "Training scene-specific model",
  "Evaluating held-out viewpoints",
  "Applying quality gate",
  "Preparing explorer"
];

export function WorkflowShell({ sceneBundle }: WorkflowShellProps) {
  const [view, setView] = useState<"select" | "processing" | "explorer">("select");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const activeProgress = jobStatus?.progress ?? 0;
  const percent = Math.round(activeProgress * 100);
  const completedStageCount = useMemo(
    () => Math.min(processingStages.length, Math.max(1, Math.ceil(activeProgress * processingStages.length))),
    [activeProgress]
  );

  useEffect(() => {
    if (!uploadResponse || view !== "processing") {
      return;
    }

    let cancelled = false;

    const poll = async () => {
      try {
        const status = await fetchJobStatus(uploadResponse.job_id);
        if (!cancelled) {
          setJobStatus(status);
        }
      } catch {
        if (!cancelled) {
          setUploadError("Processing status unavailable");
        }
      }
    };

    void poll();
    const intervalId = window.setInterval(poll, 4000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [uploadResponse, view]);

  const startUpload = async () => {
    if (!selectedFile) {
      setUploadError("Choose a walkthrough video first");
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const response = await uploadWalkthrough(selectedFile);
      setUploadResponse(response);
      setView("processing");
    } catch {
      setUploadError("Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  if (view === "explorer") {
    return <ExplorerShell sceneBundle={sceneBundle} />;
  }

  if (view === "processing") {
    return (
      <main className="workflow-screen">
        <section className="workflow-panel processing-panel" aria-label="Processing timeline">
          <div className="workflow-heading">
            <span className="workflow-icon">
              <LoaderCircle size={18} aria-hidden="true" />
            </span>
            <div>
              <h1>Processing walkthrough</h1>
              <p>{jobStatus?.message ?? "Creating processing job"}</p>
            </div>
          </div>

          <div className="progress-track" aria-label="Processing progress">
            <span style={{ width: `${percent}%` }} />
          </div>
          <div className="progress-meta">
            <span>{percent}%</span>
            <span>{uploadResponse?.estimated_processing_time_sec ?? 240}s estimate</span>
          </div>

          <ol className="stage-list">
            {processingStages.map((stage, index) => (
              <li data-active={index < completedStageCount} key={stage}>
                <CheckCircle2 size={16} aria-hidden="true" />
                {stage}
              </li>
            ))}
          </ol>

          {uploadError ? <p className="workflow-error">{uploadError}</p> : null}

          <div className="workflow-actions">
            <button className="secondary-action" onClick={() => setView("select")} type="button">
              Back
            </button>
            <button className="primary-action" onClick={() => setView("explorer")} type="button">
              Open explorer
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="workflow-screen">
      <section className="workflow-panel selection-panel" aria-label="Upload or select demo scene">
        <div className="workflow-heading">
          <span className="workflow-icon">
            <Film size={18} aria-hidden="true" />
          </span>
          <div>
            <h1>DreamNav</h1>
            <p>Works best with slow, steady indoor walkthroughs with good lighting and textured surfaces.</p>
          </div>
        </div>

        <div className="upload-target">
          <Upload size={24} aria-hidden="true" />
          <label htmlFor="walkthrough-upload">Walkthrough video</label>
          <input
            accept="video/mp4,video/quicktime,.mp4,.mov,.m4v"
            id="walkthrough-upload"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <span>{selectedFile?.name ?? "No file selected"}</span>
        </div>

        {uploadError ? <p className="workflow-error">{uploadError}</p> : null}

        <div className="demo-row" aria-label="Demo scenes">
          <button className="demo-scene" onClick={() => setView("explorer")} type="button">
            <span>{sceneBundle.demoScene.title}</span>
            <small>{sceneBundle.demoScene.description}</small>
          </button>
        </div>

        <div className="workflow-actions">
          <button
            className="primary-action"
            disabled={isUploading}
            onClick={startUpload}
            type="button"
          >
            {isUploading ? "Uploading" : "Start processing"}
          </button>
          <button className="secondary-action" onClick={() => setView("explorer")} type="button">
            Open demo
          </button>
        </div>
      </section>
    </main>
  );
}
