# 0041 PNG baseline export

Nearest-view comparison assets now prefer PNG export from pseudo-view RGB because browser-native raster images better match future renderer outputs and avoid carrying renderer pixels through SVG markup.

The SVG nearest-view card remains as a fallback only when pseudo-view RGB is missing or invalid.
