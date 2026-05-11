"use client";

import type { CameraPath } from "@dream-nav/shared";
import { confidenceZoneColors, type ConfidenceZoneArtifacts, zoneCells } from "../../lib/confidence-zones";
import type { ViewerCameraPose } from "./viewer-camera";

type MinimapProps = {
  cameraMarkers: ViewerCameraPose[];
  cameraPath: CameraPath;
  currentPose: ViewerCameraPose;
  zoneArtifacts: ConfidenceZoneArtifacts;
};

export function Minimap({ cameraMarkers, cameraPath, currentPose, zoneArtifacts }: MinimapProps) {
  const points = cameraPath.poses.map((pose) => projectPoint(pose.position[0], pose.position[2]));
  const polylinePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
  const currentPoint = projectPoint(currentPose.position[0], currentPose.position[2]);
  const facingPoint = projectFacingPoint(currentPoint, currentPose.yaw);

  return (
    <div className="minimap">
      <svg aria-label="Camera path" role="img" viewBox="0 0 120 120">
        {zoneCells(zoneArtifacts).map((cell) => {
          const point = projectPoint(cell.center[0], cell.center[2]);
          return (
            <circle
              cx={point.x}
              cy={point.y}
              fill={confidenceZoneColors[cell.zone]}
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
        {cameraMarkers.map((marker, index) => {
          const point = projectPoint(marker.position[0], marker.position[2]);
          return (
            <rect
              aria-label="Saved camera marker"
              fill="#77d7c8"
              height="6"
              key={`${marker.position.join(",")}-${index}`}
              transform={`rotate(45 ${point.x} ${point.y})`}
              width="6"
              x={point.x - 3}
              y={point.y - 3}
            />
          );
        })}
        <line
          aria-hidden="true"
          stroke="#77d7c8"
          strokeLinecap="round"
          strokeWidth="2.5"
          x1={currentPoint.x}
          x2={facingPoint.x}
          y1={currentPoint.y}
          y2={facingPoint.y}
        />
        <circle
          aria-label="Current camera position"
          cx={currentPoint.x}
          cy={currentPoint.y}
          fill="#dfe7df"
          r="4.5"
          stroke="#111412"
          strokeWidth="1.5"
        />
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

function projectFacingPoint(point: { x: number; y: number }, yaw: number): { x: number; y: number } {
  return {
    x: point.x + Math.sin(yaw) * 12,
    y: point.y - Math.cos(yaw) * 12
  };
}
