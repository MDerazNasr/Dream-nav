"use client";

import type { CompletionManifest } from "@dream-nav/shared";
import type { CachedCompletionMatch } from "./completion-preview";

type CompletionPreviewProps = {
  completion: CompletionManifest;
  match: CachedCompletionMatch | null;
};

export function CompletionPreview({ completion, match }: CompletionPreviewProps) {
  const status = completion.quality_gate === "fail" ? "Disabled" : match ? "Cached" : "No cache";

  return (
    <section className="panel" aria-label="Completion preview">
      <div className="panel-header">
        <h2 className="panel-title">Completion</h2>
        <span className="badge" aria-label="Completion cache status" data-status={completion.quality_gate}>
          {status}
        </span>
      </div>
      {match ? (
        <div className="completion-preview">
          <img alt="Cached completion prediction" src={match.rgbUrl} />
          <div className="completion-meta">
            <span>{match.prediction.prediction_id}</span>
            <span>{formatPredictionLatency(match.prediction.latency_ms_p50)}</span>
          </div>
        </div>
      ) : (
        <div className="completion-empty" aria-label="No cached completion prediction">
          {completion.quality_gate === "fail" ? "Quality gate failed" : "No planned-path cache"}
        </div>
      )}
    </section>
  );
}

function formatPredictionLatency(latencyMs: number | null): string {
  if (latencyMs === null) {
    return "TBD";
  }

  return `${latencyMs} ms`;
}
