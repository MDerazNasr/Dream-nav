# 0087 Normal Oriented Dense Surfels

Dense point-cloud imports now preserve COLMAP fused normals and emit oriented anisotropic surfel-like splats instead of isotropic blobs because the dense bridge needs surface orientation data to have any chance of reading as structure rather than a pure glow field.
