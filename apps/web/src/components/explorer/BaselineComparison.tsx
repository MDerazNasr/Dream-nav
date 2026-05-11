"use client";

import type { CameraPath, QualityReport } from "@dream-nav/shared";
import type { CachedCompletionMatch } from "./completion-preview";

type BaselineComparisonProps = {
  cameraPath: CameraPath;
  match: CachedCompletionMatch | null;
  quality: QualityReport;
};

export type NearestReferenceView = {
  cameraPoseIndex: number;
  distanceMeters: number;
  frameIndex: number;
};

export function BaselineComparison({ cameraPath, match, quality }: BaselineComparisonProps) {
  const referenceView = match
    ? selectNearestReferenceView(cameraPath, match.prediction.camera_pose_index)
    : null;

  return (
    <section className="panel" aria-label="Baseline comparison">
      <div className="panel-header">
        <h2 className="panel-title">Comparison</h2>
        <span className="badge" aria-label="Completion quality gate" data-status={quality.quality_gate}>
          {quality.quality_gate}
        </span>
      </div>
      {match && referenceView ? (
        <div className="baseline-comparison">
          <article className="baseline-method">
            <div className="baseline-method-header">
              <strong>DreamNav</strong>
              <span>{formatPsnr(quality.heldout_psnr_median)}</span>
            </div>
            <img alt="Model completion comparison" src={match.rgbUrl} />
            <dl className="baseline-stats">
              <div>
                <dt>Runtime</dt>
                <dd>{quality.runtime_path}</dd>
              </div>
              <div>
                <dt>Latency</dt>
                <dd>{formatLatency(match.prediction.latency_ms_p50)}</dd>
              </div>
            </dl>
          </article>

          <article className="baseline-method">
            <div className="baseline-method-header">
              <strong>Nearest view</strong>
              <span>{referenceView.distanceMeters.toFixed(1)} m</span>
            </div>
            <div className="baseline-placeholder" aria-label="Nearest-view baseline placeholder">
              <strong>Frame {referenceView.frameIndex}</strong>
              <span>Pose {referenceView.cameraPoseIndex}</span>
            </div>
            <dl className="baseline-stats">
              <div>
                <dt>Method</dt>
                <dd>Lookup</dd>
              </div>
              <div>
                <dt>Target</dt>
                <dd>Pose {match.prediction.camera_pose_index}</dd>
              </div>
            </dl>
          </article>
        </div>
      ) : (
        <div className="completion-empty" aria-label="No baseline comparison">
          No cached comparison
        </div>
      )}
    </section>
  );
}

export function selectNearestReferenceView(
  cameraPath: CameraPath,
  targetPoseIndex: number
): NearestReferenceView | null {
  const targetPose = cameraPath.poses[targetPoseIndex] ?? cameraPath.poses[0];
  if (!targetPose) {
    return null;
  }

  return cameraPath.poses
    .map((pose, cameraPoseIndex) => ({
      cameraPoseIndex,
      distanceMeters: positionDistance(targetPose.position, pose.position),
      frameIndex: pose.frame_index
    }))
    .filter((candidate) => candidate.cameraPoseIndex !== targetPoseIndex)
    .sort((a, b) => a.distanceMeters - b.distanceMeters)[0] ?? null;
}

function formatLatency(latencyMs: number | null): string {
  return latencyMs === null ? "TBD" : `${latencyMs} ms`;
}

function formatPsnr(psnr: number | null): string {
  return psnr === null ? "PSNR TBD" : `${psnr.toFixed(1)} dB`;
}

function positionDistance(a: readonly [number, number, number], b: readonly [number, number, number]): number {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  const dz = a[2] - b[2];
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}
