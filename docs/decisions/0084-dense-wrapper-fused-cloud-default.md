## Decision

The COLMAP dense wrapper now normalizes the fused dense cloud directly and keeps up to `50000` points, instead of applying the current camera path point filter before writing the splat.

## Why

On the denser `117` frame Runpod reconstruction, the raw fused cloud import produced materially better coverage than the worker's filtered `40000` point splat output. The current path filter is no longer a safe default because it can over trim the dense cloud and collapse the imported scene quality.

## Consequence

Future dense worker callbacks will preserve more of the fused reconstruction and match the better path we already observed in the live imported result, while leaving stricter dense cloud trimming for a later, better grounded heuristic.
