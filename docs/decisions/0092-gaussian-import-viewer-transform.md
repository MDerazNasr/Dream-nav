# 0092 Gaussian Import Viewer Transform

Remote Nerfstudio Gaussian results are imported into DreamNav by transforming splat positions and rotations from the worker's raw COLMAP or Nerfstudio coordinate frame into `dreamnav_viewer_v1`, because the app's camera path and navigation operate in viewer coordinates rather than the training coordinate system.
