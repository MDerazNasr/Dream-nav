# 0049 Colmap sparse splat wrapper

DreamNav now promotes the Gaussian stage to a real internal command when `colmap` is available by converting the selected COLMAP sparse `points3D.txt` model into a valid `splat.ply`, because this moves the pipeline from placeholder geometry to generated scene assets without waiting for a full external 3DGS trainer.

The wrapper still produces a sparse reconstruction rather than a dense high quality Gaussian scene, so it is a bridge to real geometry rather than the final reconstruction backend.
