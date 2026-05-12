# 0050 Featured generated scene

DreamNav now prefers the latest completed job scene that came through the real COLMAP plus Gaussian command path because the homepage should surface an actual generated reconstruction when one exists instead of keeping users on the static placeholder demo.

The fallback to `warehouse_01` remains in place so the app still opens cleanly on machines that do not yet have a completed reconstructed scene bundle.
