# 0047 Auto ffmpeg frame default

DreamNav now prefers `ffmpeg` for live frame extraction when the binary is already installed because the upload flow should advance toward real reconstruction on capable machines without requiring an environment override for the first pipeline stage.

Pure test settings still keep the explicit `stub` default so worker unit tests remain deterministic.
