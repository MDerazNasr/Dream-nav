"use client";

import type { GaussianImportResponse, RemoteDenseResultSummary, RemoteDenseSubmissionResponse } from "@dream-nav/shared";
import { useEffect, useState } from "react";
import { fetchGaussianImportReview, fetchRemoteDenseResultSummary, submitRemoteDenseJob } from "../../lib/dreamnav-api";

type RemoteDensePanelProps = {
  jobId: string;
};

const POLL_INTERVAL_MS = 4000;

export function RemoteDensePanel({ jobId }: RemoteDensePanelProps) {
  const [message, setMessage] = useState<string | null>(null);
  const [review, setReview] = useState<GaussianImportResponse | null>(null);
  const [resultSummary, setResultSummary] = useState<RemoteDenseResultSummary | null>(null);
  const [submission, setSubmission] = useState<RemoteDenseSubmissionResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!submission || (review && resultSummary)) {
      return;
    }

    let cancelled = false;

    const poll = async () => {
      try {
        const [nextReview, nextResultSummary] = await Promise.all([
          fetchGaussianImportReview(jobId),
          fetchRemoteDenseResultSummary(jobId)
        ]);
        if (!cancelled) {
          if (nextReview) {
            setReview(nextReview);
          }
          if (nextResultSummary) {
            setResultSummary(nextResultSummary);
          }
        }
      } catch {
        if (!cancelled) {
          setMessage("Remote dense review is not available yet");
        }
      }
    };

    void poll();
    const intervalId = window.setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [jobId, resultSummary, review, submission]);

  const submitJob = async () => {
    setIsSubmitting(true);
    setMessage(null);
    setReview(null);
    setResultSummary(null);

    try {
      const nextSubmission = await submitRemoteDenseJob(jobId);
      setSubmission(nextSubmission);
    } catch {
      setMessage("Remote dense submission failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="upload-target remote-dense-panel" aria-label="Remote dense backend">
      <span className="upload-title">Remote dense backend</span>
      <p className="import-copy">
        Send this completed job to the configured remote dense worker and let the returned `.ply` land back in DreamNav automatically.
      </p>
      {message ? <p className="workflow-error">{message}</p> : null}
      {submission ? (
        <section className="import-review" aria-label="Remote dense submission review">
          <div className="import-review-header">
            <span className="readiness-pill" data-status={review ? reviewStatus(review.validation_status) : "degraded"}>
              {review ? labelForValidation(review.validation_status) : "Submitted"}
            </span>
            <small>
              {review
                ? review.blockers[0] ?? review.warnings[0] ?? "Remote dense result received."
                : "Waiting for the remote worker to post the imported dense result back."}
            </small>
          </div>
          <div className="remote-dense-grid">
            <article>
              <span>Provider</span>
              <strong>{submission.provider_url}</strong>
            </article>
            <article>
              <span>Remote job</span>
              <strong>{submission.remote_job_id ?? "Queued"}</strong>
            </article>
            <article>
              <span>Backend</span>
              <strong>{submission.backend ?? "Unknown"}</strong>
            </article>
            <article>
              <span>Frames</span>
              <strong>{submission.frame_count.toLocaleString()}</strong>
            </article>
            <article>
              <span>Bundle</span>
              <strong>{submission.bundle_file}</strong>
            </article>
            <article>
              <span>Callback</span>
              <strong>{review ? "Imported" : "Waiting"}</strong>
            </article>
            <article>
              <span>Result backend</span>
              <strong>{resultSummary?.backend ?? "Waiting"}</strong>
            </article>
            <article>
              <span>Result job</span>
              <strong>{resultSummary?.remote_job_id ?? "Waiting"}</strong>
            </article>
          </div>
          {submission.warnings.map((warning) => (
            <small key={warning}>{warning}</small>
          ))}
          {resultSummary ? (
            <small>
              Imported `{resultSummary.source_file}` via {resultSummary.backend ?? "unknown"} backend.
            </small>
          ) : null}
          {review ? <small>Open processed scene to inspect the imported dense result.</small> : null}
        </section>
      ) : null}
      <div className="import-actions">
        <button className="secondary-action" disabled={isSubmitting} onClick={submitJob} type="button">
          {isSubmitting ? "Submitting remote dense job" : "Submit to remote dense backend"}
        </button>
      </div>
    </section>
  );
}

function labelForValidation(status: GaussianImportResponse["validation_status"]): string {
  if (status === "pass") {
    return "Approved";
  }

  if (status === "warning") {
    return "Needs review";
  }

  return "Rejected";
}

function reviewStatus(status: GaussianImportResponse["validation_status"]): "ready" | "degraded" | "blocked" {
  if (status === "pass") {
    return "ready";
  }

  if (status === "warning") {
    return "degraded";
  }

  return "blocked";
}
