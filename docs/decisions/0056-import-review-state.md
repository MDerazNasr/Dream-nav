# 0056 Import Review State

## Decision

Show a post-import review state on the completed-job screen before opening the explorer.

## Why

Imported dense assets can change observed coverage, completion coverage, and featured-scene eligibility. Opening the explorer immediately hides that validation context and makes it harder to tell whether the imported scene actually improved the job.

## Consequences

The completed-job workflow now imports first, shows refreshed scene metrics, and only opens the explorer after an explicit user action. This keeps the import flow transparent and makes the refreshed scene state visible before presentation.
