"use client";

import type { CameraPath, VisibilityManifest } from "@dream-nav/shared";

type MinimapProps = {
  cameraPath: CameraPath;
  visibility: VisibilityManifest;
};

export function Minimap({ cameraPath, visibility }: MinimapProps) {
  const points = cameraPath.poses.map((pose) => projectPoint(pose.position[0], pose.position[2]));
  const polylinePoints = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="minimap">
      <svg aria-label="Camera path" role="img" viewBox="0 0 120 120">
        {visibility.cells.map((cell) => {
          const point = projectPoint(cell.center[0], cell.center[2]);
          return (
            <circle
              cx={point.x}
              cy={point.y}
              fill={zoneColor(cell.zone)}
              key={cell.cell_id}
              opacity="0.68"
              r="7"
            />
          );
        })}
        <polyline
          fill="none"
          points={polylinePoints}
          stroke="#f5f7f4"
          strokeLinecap="round"
          strokeWidth="3"
        />
        {points.map((point, index) => (
          <circle cx={point.x} cy={point.y} fill="#f0c95a" key={index} r={index === 0 ? 4 : 3} />
        ))}
      </svg>
    </div>
  );
}

function projectPoint(x: number, z: number): { x: number; y: number } {
  return {
    x: 60 + x * 20,
    y: 60 + z * 20
  };
}

function zoneColor(zone: string): string {
  if (zone === "observed") {
    return "#dfe7df";
  }

  if (zone === "partial") {
    return "#77d7c8";
  }

  if (zone === "completion") {
    return "#4a8ee8";
  }

  return "#d88b4a";
}
