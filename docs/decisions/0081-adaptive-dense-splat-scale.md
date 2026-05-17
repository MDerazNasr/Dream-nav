## 0081. Adaptive dense splat scale

The dense point cloud to splat conversion now expands point size from local nearest neighbor spacing instead of assigning one fixed scale to every imported point.

This keeps compact areas crisp while giving sparse dense reconstructions enough footprint to read as surfaces instead of dim isolated specks.
