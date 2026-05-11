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
    ratios = _zone_ratios(cells)
    return {
        "scene_id": scene_id,
        "method": _string_value(visibility_support, "method", "voxel_visibility_v1"),
        "observed_threshold": observed_threshold,
        "partial_threshold": [1, max(1, observed_threshold - 1)],
        "observed_ratio": ratios["observed"],
        "partial_ratio": ratios["partial"],
        "completion_candidate_ratio": ratios["completion"],
        "unknown_ratio": ratios["unknown"],
        "cells": cells,
    }


def _visibility_cells(
    splat_points: list[SplatPoint],
    poses: list[PosePoint],
    observed_threshold: int,
) -> list[dict[str, object]]:
    cells = []
    for index, point in enumerate(splat_points[:64]):
        visibility_count = _visibility_count(point, poses)
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


def _visibility_count(point: SplatPoint, poses: list[PosePoint]) -> int:
    support = 0
    for pose in poses:
        distance = _distance(point, pose)
        if distance <= 1.2:
            support += 2
        elif distance <= 2.4:
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


def _int_value(payload: dict[str, Any], key: str, default: int = 0) -> int:
    value = payload.get(key, default)
    return int(value) if isinstance(value, int | float) else default


def _string_value(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key, default)
    return value if isinstance(value, str) and value else default
