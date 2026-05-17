## 0080. Robust dense framing and filtering

The explorer now opens splat scenes without the confidence overlay or synthetic floor by default, and it uses a compact overview distance for small reconstructed scenes.

The dense COLMAP wrapper now filters points against a robust camera pose cluster instead of raw path extrema so outlier poses do not keep off path junk geometry in the imported scene.
