"use client";

import type { ReconstructionCapabilities } from "@dream-nav/shared";

type ReconstructionStatusPanelProps = {
  capabilities: ReconstructionCapabilities;
};

export function ReconstructionStatusPanel({ capabilities }: ReconstructionStatusPanelProps) {
  return (
    <section className="reconstruction-panel" aria-label="Reconstruction pipeline">
      <div className="workflow-heading">
        <div>
          <h2>Reconstruction</h2>
          <p>
            {capabilities.pipeline_status === "real"
              ? "This machine is configured for a real reconstruction run."
              : "This machine is not fully configured for a real 3D reconstruction yet."}
          </p>
        </div>
      </div>

      <div className="reconstruction-summary">
        <span className="readiness-pill" data-status={pillStatus(capabilities.pipeline_status)}>
          {labelForStatus(capabilities.pipeline_status)}
        </span>
        <small>
          Frames: {capabilities.frame_backend} · Poses: {capabilities.pose_backend} · Gaussian:{" "}
          {capabilities.gaussian_backend}
        </small>
      </div>

      {capabilities.missing_requirements.length > 0 ? (
        <ul className="reconstruction-list">
          {capabilities.missing_requirements.map((requirement) => (
            <li key={requirement}>{requirement}</li>
          ))}
        </ul>
      ) : null}

      {capabilities.warnings.length > 0 ? (
        <ul className="reconstruction-list" data-tone="warning">
          {capabilities.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function labelForStatus(status: ReconstructionCapabilities["pipeline_status"]): string {
  if (status === "real") {
    return "Real pipeline";
  }

  if (status === "mixed") {
    return "Partial pipeline";
  }

  return "Stub pipeline";
}

function pillStatus(status: ReconstructionCapabilities["pipeline_status"]): "blocked" | "degraded" | "ready" {
  if (status === "real") {
    return "ready";
  }

  if (status === "mixed") {
    return "degraded";
  }

  return "blocked";
}
