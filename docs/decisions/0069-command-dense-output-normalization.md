## Context

The remote dense command backend previously assumed every real engine would write a DreamNav-ready splat PLY, which is too restrictive for practical dense engines that often emit standard point-cloud PLY output first.

## Decision

Normalize command backend output inside the remote worker so external dense engines can return either a viewer-ready splat PLY or a standard dense point-cloud PLY.

## Consequences

Real dense engines no longer need DreamNav-specific splat export logic on day one, and the worker can bridge ordinary dense point-cloud output into the viewer format before the callback import path runs.
