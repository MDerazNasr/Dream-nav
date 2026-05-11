# Nearest View Baseline Asset

Cached completion predictions now include a nearest-view baseline asset and pose index because the comparison panel should render concrete baseline imagery instead of only describing the fallback.

Job-owned baseline SVGs are converted from the nearest pseudo-view RGB output so the browser can display the current PPM renderer output without adding another frontend image decoder.
