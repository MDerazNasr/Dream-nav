# 0086 Camera Bounds Point Cloud Import

Imported dense point clouds now pass through a conservative camera-path bounds crop before splat conversion because fused COLMAP clouds were carrying extreme off-scene outliers that distorted sampling, visibility, and viewer framing more than they improved reconstruction coverage.
