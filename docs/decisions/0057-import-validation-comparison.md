# 0057 Import Validation Comparison

## Decision

Add explicit pass, warning, and reject validation states for imported dense assets, and show before and after review metrics before the imported scene can be opened.

## Why

An imported `.ply` can improve scene density while still being misaligned with the recovered camera path. Numeric refresh alone is not enough if the workflow does not tell the user whether the imported result is acceptable, degraded, or blocked.

## Consequences

The import route now returns validation status, blockers, warnings, and previous versus current scene metrics. The completed-job review panel uses that response to show a direct comparison and prevents opening imports that fail the new reject gate.
