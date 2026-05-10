import type { LensMode } from "@dream-nav/shared";

const lensFovDegrees: Record<LensMode, number> = {
  "24mm": 73,
  "35mm": 54,
  "50mm": 40,
  "85mm": 24
};

export function getLensFov(lensMode: LensMode): number {
  return lensFovDegrees[lensMode];
}
