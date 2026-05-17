# 0088 Trained Gaussian Worker Slot

The remote dense worker now has a first-class `gaussian_command` backend and prefers it ahead of the COLMAP fused-point bridge in `auto` mode because the current point-cloud-to-splat path has reached its visual quality ceiling and the product needs a clean path to a true Gaussian reconstruction engine.
