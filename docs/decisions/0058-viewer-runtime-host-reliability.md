# 0058 Viewer Runtime Host Reliability

## Decision

Make the viewer verification flow use `localhost:3001` by default, allow `127.0.0.1` as a development origin, and fail API requests quickly enough to show the existing unavailable state instead of hanging on the loading screen.

## Why

The web app was rendering static HTML under `127.0.0.1:3001` without becoming interactive because Next.js dev resources were blocked for that origin. At the same time, when the API was down, the home page could sit on `Preparing explorer` while server-side fetches waited too long to fail.

## Consequences

Viewer automation now opens the same host that the local dev server advertises, manual `127.0.0.1` access remains valid in development, and API outages surface as a fast failure path instead of a misleading endless loading state.
