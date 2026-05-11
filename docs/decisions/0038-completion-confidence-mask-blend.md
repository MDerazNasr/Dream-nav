# Completion Confidence Mask Blend

Cached completion projections now use the prediction confidence mask as an alpha map because model output should only appear strongly where the completion artifact marks supported predicted pixels.

The current mask remains a preview artifact rather than calibrated uncertainty until the completion model writes learned confidence or depth-aware validity masks.

