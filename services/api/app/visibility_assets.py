from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Any

from .splat_assets import SplatAssetError, SplatPoint, read_splat_points


class VisibilityBuildError(Exception):
    pass


@dataclass(frozen=True)
class PosePoint:
    x: float
    y: float
    z: float


def build_visibility_manifest(
    scene_id: str,
    camera_path: dict[str, Any],
    splat_path: Path,
    visibility_support: dict[str, Any],
) -> dict[str, object]:
    poses = _pose_points(camera_path)
    observed_threshold = _int_value(visibility_support, "observed_threshold", default=3)
    try:
        splat_points = read_splat_points(splat_path)
    except SplatAssetError as error:
        raise VisibilityBuildError(str(error)) from error

    cells = _visibility_cells(splat_points, poses, observed_threshold)
    method = _string_value(visibility_support, "method", "voxel_visibility_v1")
    adaptive_thresholds = None
    if _needs_adaptive_visibility(cells, splat_points):
        near_radius, far_radius = _adaptive_distance_thresholds(splat_points, poses)
        cells = _visibility_cells(
            splat_points,
            poses,
            observed_threshold,
            near_radius=near_radius,
            far_radius=far_radius,
        )
        adaptive_thresholds = {
            "near_radius_meters": round(near_radius, 3),
            "far_radius_meters": round(far_radius, 3),
        }
        method = f"{method}_adaptive"
    ratios = _zone_ratios(cells)
    manifest = {
        "scene_id": scene_id,
        "method": method,
        "observed_threshold": observed_threshold,
        "partial_threshold": [1, max(1, observed_threshold - 1)],
        "observed_ratio": ratios["observed"],
        "partial_ratio": ratios["partial"],
        "completion_candidate_ratio": ratios["completion"],
        "unknown_ratio": ratios["unknown"],
        "cells": cells,
    }
    if adaptive_thresholds is not None:
        manifest["adaptive_thresholds"] = adaptive_thresholds
    return manifest


def _visibility_cells(
    splat_points: list[SplatPoint],
    poses: list[PosePoint],
    observed_threshold: int,
    near_radius: float = 1.2,
    far_radius: float = 2.4,
) -> list[dict[str, object]]:
    cells = []
    for index, point in enumerate(splat_points[:64]):
        visibility_count = _visibility_count(point, poses, near_radius, far_radius)
        cells.append(
            {
                "cell_id": f"cell_{index:03d}",
                "center": [round(point.x, 4), round(point.y, 4), round(point.z, 4)],
                "size_meters": 0.5,
                "visibility_count": visibility_count,
                "zone": _zone_for_count(visibility_count, observed_threshold),
            }
        )

    if all(cell["zone"] != "completion" for cell in cells):
        completion_anchor = _completion_anchor(splat_points, poses)
        cells.append(
            {
                "cell_id": f"cell_{len(cells):03d}",
                "center": completion_anchor,
                "size_meters": 0.5,
                "visibility_count": 0,
                "zone": "completion",
            }
        )

    return cells


def _visibility_count(point: SplatPoint, poses: list[PosePoint], near_radius: float, far_radius: float) -> int:
    support = 0
    for pose in poses:
        distance = _distance(point, pose)
        if distance <= near_radius:
            support += 2
        elif distance <= far_radius:
            support += 1

    return support


def _zone_for_count(visibility_count: int, observed_threshold: int) -> str:
    if visibility_count >= observed_threshold:
        return "observed"

    if visibility_count > 0:
        return "partial"

    return "completion"


def _zone_ratios(cells: list[dict[str, object]]) -> dict[str, float]:
    total = max(1, len(cells))
    return {
        "observed": _rounded_ratio(cells, "observed", total),
        "partial": _rounded_ratio(cells, "partial", total),
        "completion": _rounded_ratio(cells, "completion", total),
        "unknown": _rounded_ratio(cells, "unknown", total),
    }


def _rounded_ratio(cells: list[dict[str, object]], zone: str, total: int) -> float:
    return round(sum(1 for cell in cells if cell["zone"] == zone) / total, 4)


def _pose_points(camera_path: dict[str, Any]) -> list[PosePoint]:
    poses = camera_path.get("poses")
    if not isinstance(poses, list):
        raise VisibilityBuildError("Camera path poses are required for visibility.")

    points = []
    for pose in poses:
        if not isinstance(pose, dict):
            continue
        position = pose.get("position")
        if isinstance(position, list) and len(position) == 3:
            points.append(PosePoint(float(position[0]), float(position[1]), float(position[2])))

    if not points:
        raise VisibilityBuildError("Camera path did not contain readable pose positions.")

    return points


def _completion_anchor(splat_points: list[SplatPoint], poses: list[PosePoint]) -> list[float]:
    last_pose = poses[-1]
    farthest = max(splat_points, key=lambda point: _distance(point, last_pose))
    dx = farthest.x - last_pose.x
    dz = farthest.z - last_pose.z
    length = sqrt(dx * dx + dz * dz) or 1
    return [
        round(farthest.x + dx / length * 0.8, 4),
        round(farthest.y, 4),
        round(farthest.z + dz / length * 0.8, 4),
    ]


def _distance(point: SplatPoint, pose: PosePoint) -> float:
    return sqrt((point.x - pose.x) ** 2 + (point.y - pose.y) ** 2 + (point.z - pose.z) ** 2)


def _needs_adaptive_visibility(cells: list[dict[str, object]], splat_points: list[SplatPoint]) -> bool:
    if len(splat_points) < 64:
        return False

    observed_ratio = _rounded_ratio(cells, "observed", max(1, len(cells)))
    completion_ratio = _rounded_ratio(cells, "completion", max(1, len(cells)))
    return observed_ratio == 0 and completion_ratio >= 0.9


def _adaptive_distance_thresholds(splat_points: list[SplatPoint], poses: list[PosePoint]) -> tuple[float, float]:
    nearest_distances = sorted(
        min(_distance(point, pose) for pose in poses)
        for point in splat_points[:128]
    )
    if not nearest_distances:
        return 2.4, 4.0

    near_radius = _clamp(_percentile(nearest_distances, 0.55), 2.4, 10.0)
    far_radius = _clamp(max(near_radius + 1.5, _percentile(nearest_distances, 0.9)), 4.0, 14.0)
    return near_radius, far_radius


def _percentile(sorted_values: list[float], quantile: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, int((len(sorted_values) - 1) * quantile)))
    return sorted_values[index]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _int_value(payload: dict[str, Any], key: str, default: int = 0) -> int:
    value = payload.get(key, default)
    return int(value) if isinstance(value, int | float) else default


def _string_value(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key, default)
    return value if isinstance(value, str) and value else default
