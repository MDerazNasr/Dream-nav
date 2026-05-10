"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="system-state">
      <p className="state-label">Scene API unavailable</p>
      <button className="state-button" onClick={reset} type="button">
        Retry
      </button>
    </main>
  );
}
