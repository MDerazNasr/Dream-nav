import type { VisibilityManifest, VisibilityZone, ZoneArtifact } from "@dream-nav/shared";

export type ConfidenceZoneArtifacts = Record<VisibilityZone, ZoneArtifact>;

export const confidenceZoneOrder: VisibilityZone[] = [
  "observed",
  "partial",
  "completion",
  "unknown"
];

export const confidenceZoneLabels: Record<VisibilityZone, string> = {
  observed: "Observed",
  partial: "Partial",
  completion: "Completion",
  unknown: "Unknown"
};

export const confidenceZoneColors: Record<VisibilityZone, string> = {
  observed: "#dfe7df",
  partial: "#77d7c8",
  completion: "#4a8ee8",
  unknown: "#d88b4a"
};

export function buildZoneArtifactsFromVisibility(
  sceneId: string,
  visibility: VisibilityManifest
): ConfidenceZoneArtifacts {
  const totalCells = Math.max(1, visibility.cells.length);
  return Object.fromEntries(
    confidenceZoneOrder.map((zone) => {
      const cells = visibility.cells.filter((cell) => cell.zone === zone);
      return [
        zone,
        {
          scene_id: sceneId,
          zone,
          source_manifest: "visibility_manifest.json",
          cell_count: cells.length,
          coverage_ratio: roundRatio(cells.length / totalCells),
          bounds: boundsForCells(cells),
          cells
        }
      ];
    })
  ) as ConfidenceZoneArtifacts;
}

export function zoneCells(zoneArtifacts: ConfidenceZoneArtifacts): ZoneArtifact["cells"] {
  return confidenceZoneOrder.flatMap((zone) => zoneArtifacts[zone].cells);
}

function boundsForCells(cells: ZoneArtifact["cells"]): ZoneArtifact["bounds"] {
  if (cells.length === 0) {
    return null;
  }

  return {
    min: [
      roundCoordinate(Math.min(...cells.map((cell) => cell.center[0]))),
      roundCoordinate(Math.min(...cells.map((cell) => cell.center[1]))),
      roundCoordinate(Math.min(...cells.map((cell) => cell.center[2])))
    ],
    max: [
      roundCoordinate(Math.max(...cells.map((cell) => cell.center[0]))),
      roundCoordinate(Math.max(...cells.map((cell) => cell.center[1]))),
      roundCoordinate(Math.max(...cells.map((cell) => cell.center[2])))
    ]
  };
}

function roundRatio(value: number): number {
  return Math.round(value * 10000) / 10000;
}

function roundCoordinate(value: number): number {
  return Math.round(value * 10000) / 10000;
}
