## Decision

The local COLMAP mapper timeout now scales at `6` seconds per extracted frame, with a hard ceiling of `900` seconds.

## Why

The denser `4` FPS extraction default doubled the source coverage for the same walkthrough, but the local mapper still timed out because the old `3` seconds per frame budget stopped at roughly `351` seconds for a `117` frame run. That budget is too low for room scale clips on a laptop once reconstruction coverage improves.

## Consequence

Local uploads can take materially longer during camera motion recovery, but denser frame sets are no longer forced to fail just because the mapper budget was tuned around the older sparse extraction default.
