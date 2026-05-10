"use client";

import type { JobStatus, ProcessingStage, UploadResponse } from "@dream-nav/shared";
import { AlertTriangle, CheckCircle2, Film, LoaderCircle, RotateCcw, Upload, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ExplorerShell } from "../explorer/ExplorerShell";
import type { ViewerSceneBundle } from "../../lib/dreamnav-api";
import { fetchJobStatus, uploadWalkthrough } from "../../lib/dreamnav-api";

type WorkflowShellProps = {
  sceneBundle: ViewerSceneBundle;
};

type ProcessingStageItem = {
  stage: Exclude<ProcessingStage, "completed" | "failed">;
  label: string;
};

const processingStages: ProcessingStageItem[] = [
  { stage: "checking_capture_quality", label: "Checking capture quality" },
  { stage: "extracting_video_frames", label: "Extracting video frames" },
  { stage: "estimating_camera_motion", label: "Estimating camera motion" },
  { stage: "building_gaussian_scene", label: "Building Gaussian scene" },
  { stage: "computing_visibility_support", label: "Computing visibility support" },
  { stage: "rendering_training_views", label: "Rendering training views" },
  { stage: "training_scene_model", label: "Training scene-specific model" },
  { stage: "evaluating_heldout_viewpoints", label: "Evaluating held-out viewpoints" },
  { stage: "applying_quality_gate", label: "Applying quality gate" },
  { stage: "preparing_explorer", label: "Preparing explorer" }
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
  const jobCompleted = jobStatus?.state === "completed";
  const jobFailed = jobStatus?.state === "failed";
  const completedStageCount = useMemo(
    () => Math.min(processingStages.length, Math.ceil(activeProgress * processingStages.length)),
    [activeProgress]
  );
  const failedStageLabel = getStageLabel(jobStatus?.failed_stage);
  const failureGuidance = getFailureGuidance(jobStatus?.failed_stage, jobStatus?.error_message);

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

  const returnToUpload = () => {
    setView("select");
    setUploadResponse(null);
    setJobStatus(null);
    setUploadError(null);
    setIsUploading(false);
  };

  if (view === "explorer") {
    return <ExplorerShell sceneBundle={sceneBundle} />;
  }

  if (view === "processing") {
    return (
      <main className="workflow-screen">
        <section className="workflow-panel processing-panel" aria-label="Processing timeline">
          <div className="workflow-heading">
            <span className="workflow-icon" data-state={jobFailed ? "failed" : "running"}>
              {jobFailed ? (
                <AlertTriangle size={18} aria-hidden="true" />
              ) : (
                <LoaderCircle size={18} aria-hidden="true" />
              )}
            </span>
            <div>
              <h1>{jobFailed ? "Processing stopped" : "Processing walkthrough"}</h1>
              <p>
                {jobFailed && failedStageLabel
                  ? `Failed while ${failedStageLabel.toLowerCase()}.`
                  : jobFailed
                    ? failureGuidance.summary
                    : jobStatus?.message ?? "Creating processing job"}
              </p>
            </div>
          </div>

          <div className="progress-track" data-state={jobFailed ? "failed" : "running"} aria-label="Processing progress">
            <span style={{ width: `${percent}%` }} />
          </div>
          <div className="progress-meta">
            <span>{percent}%</span>
            <span>{jobFailed ? "Stopped" : `${uploadResponse?.estimated_processing_time_sec ?? 240}s estimate`}</span>
          </div>

          <ol className="stage-list">
            {processingStages.map((stage, index) => (
              <li data-active={index < completedStageCount} data-state={jobFailed ? "failed" : "running"} key={stage.stage}>
                {jobFailed && index === completedStageCount - 1 ? (
                  <XCircle size={16} aria-hidden="true" />
                ) : (
                  <CheckCircle2 size={16} aria-hidden="true" />
                )}
                {stage.label}
              </li>
            ))}
          </ol>

          {uploadError ? <p className="workflow-error">{uploadError}</p> : null}
          {jobFailed ? (
            <section className="failure-panel" aria-label="Processing failure details">
              {failedStageLabel ? <p>Pipeline stage: {failedStageLabel}</p> : null}
              <strong>{jobStatus.error_message ?? "Processing failed"}</strong>
              {jobStatus.failed_artifact ? <p>Debug artifact: {jobStatus.failed_artifact}</p> : null}
              <p>{failureGuidance.nextStep}</p>
            </section>
          ) : null}

          <div className="workflow-actions">
            <button className="secondary-action" onClick={returnToUpload} type="button">
              {jobFailed ? (
                <>
                  <RotateCcw size={16} aria-hidden="true" />
                  Choose another video
                </>
              ) : (
                "Back"
              )}
            </button>
            <button
              className="primary-action"
              disabled={!jobCompleted}
              onClick={() => setView("explorer")}
              type="button"
            >
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
          <span className="upload-title">Walkthrough video</span>
          <label className="file-picker" htmlFor="walkthrough-upload">
            Choose video
          </label>
          <input
            aria-label="Walkthrough video"
            accept="video/mp4,video/quicktime,.mp4,.mov,.m4v"
            className="file-input"
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

function getStageLabel(stage: JobStatus["failed_stage"]): string | null {
  return processingStages.find((stageItem) => stageItem.stage === stage)?.label ?? null;
}

function getFailureGuidance(
  failedStage: JobStatus["failed_stage"],
  errorMessage: string | null | undefined
): { summary: string; nextStep: string } {
  const message = errorMessage?.toLowerCase() ?? "";

  if (failedStage === "checking_capture_quality" || message.includes("empty")) {
    return {
      summary: "The uploaded file did not contain usable video data.",
      nextStep: "Choose a non-empty MP4, MOV, or M4V walkthrough and start processing again."
    };
  }

  if (
    failedStage === "extracting_video_frames" ||
    message.includes("frame extraction") ||
    message.includes("ffmpeg") ||
    message.includes("jpeg")
  ) {
    return {
      summary: "DreamNav could not turn the walkthrough into usable image frames.",
      nextStep: "Try a shorter, standard phone video with steady motion and good lighting."
    };
  }

  if (failedStage === "estimating_camera_motion" || message.includes("colmap") || message.includes("pose")) {
    return {
      summary: "DreamNav could not recover the camera path for this walkthrough.",
      nextStep: "Try a slower walkthrough with more textured surfaces and less motion blur."
    };
  }

  return {
    summary: "DreamNav could not finish this processing job.",
    nextStep: "Choose another video or use the demo scene while this pipeline stage is being checked."
  };
}
