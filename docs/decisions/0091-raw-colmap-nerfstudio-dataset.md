# 0091 Raw COLMAP Nerfstudio Dataset

Nerfstudio training now consumes raw COLMAP cameras and images, with the matching COLMAP applied transform on the sparse point cloud, because the DreamNav viewer camera path is a normalized presentation coordinate system and is not reliable training input.
