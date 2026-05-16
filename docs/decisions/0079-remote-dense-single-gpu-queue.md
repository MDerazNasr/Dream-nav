## 0079. Remote dense single GPU queue

The remote dense worker now serializes dense jobs with a single process wide semaphore.

This avoids overlapping COLMAP dense stereo runs on the same GPU, which degraded runtime and made submitted jobs appear stalled even when they were still waiting for compute.
