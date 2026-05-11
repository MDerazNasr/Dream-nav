# 0042 PSNR quality gate policy

Processed scenes now derive pass, warning, and fail gate status from held-out PSNR because completion reliability should come from the evaluation artifact instead of a hardcoded demo status.

The quality report carries both the gate and the viewer policy so the browser can disable failed completion and label warning completion without duplicating threshold logic.
