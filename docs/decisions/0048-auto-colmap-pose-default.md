# 0048 Auto colmap pose default

DreamNav now prefers `colmap` for live pose recovery when the binary is already installed because the upload path should advance to real camera motion estimation on capable machines without requiring an environment override for the second reconstruction stage.

Pure test settings still keep the explicit `stub` pose backend so worker coverage remains deterministic and isolated from machine-level dependencies.
