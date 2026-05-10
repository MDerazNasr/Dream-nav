# 0006 Browser Splat Loader

DreamNav uses `@mkkellogg/gaussian-splats-3d` for browser splat rendering because the project already depends on Three.js and the package directly supports INRIA `.ply` splat files.

The web app sends COOP and COEP headers because the splat renderer uses worker-backed shared memory for sorting, and that path matches the performance target better than disabling shared memory.
