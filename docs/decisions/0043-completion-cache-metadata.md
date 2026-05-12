# 0043 Completion cache metadata

Cached completion predictions now record cache key, source, status, runtime path, generation time, and P95 latency because the planned-path cache should expose the same operational shape as future live inference.

The browser displays cache diagnostics from the manifest instead of inferring cache behavior from asset names.
