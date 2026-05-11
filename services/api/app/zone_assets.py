from __future__ import annotations

from typing import Any

ZONE_FILE_NAMES = (
    "observed_zone.json",
    "partial_zone.json",
    "completion_zone.json",
    "unknown_zone.json",
)

ZONE_FILE_BY_NAME = {
    "observed": "observed_zone.json",
    "partial": "partial_zone.json",
    "completion": "completion_zone.json",
    "unknown": "unknown_zone.json",
}


class ZoneAssetBuildError(Exception):
    pass


def build_zone_artifacts(
    scene_id: str,
    visibility_manifest: dict[str, Any],
) -> dict[str, dict[str, object]]:
    cells = visibility_manifest.get("cells")
    if not isinstance(cells, list):
        raise ZoneAssetBuildError("Visibility manifest cells are required for zone artifacts.")

    artifacts = {}
    total_cells = max(1, len(cells))
    for zone, file_name in ZONE_FILE_BY_NAME.items():
        zone_cells = [cell for cell in cells if isinstance(cell, dict) and cell.get("zone") == zone]
        artifacts[file_name] = {
            "scene_id": scene_id,
            "zone": zone,
            "source_manifest": "visibility_manifest.json",
            "cell_count": len(zone_cells),
            "coverage_ratio": round(len(zone_cells) / total_cells, 4),
            "bounds": _bounds(zone_cells),
            "cells": zone_cells,
        }

    return artifacts


def _bounds(cells: list[object]) -> dict[str, list[float]] | None:
    centers = [_center(cell) for cell in cells]
    valid_centers = [center for center in centers if center is not None]
    if not valid_centers:
        return None

    return {
        "min": [round(min(center[index] for center in valid_centers), 4) for index in range(3)],
        "max": [round(max(center[index] for center in valid_centers), 4) for index in range(3)],
    }


def _center(cell: object) -> list[float] | None:
    if not isinstance(cell, dict):
        return None

    center = cell.get("center")
    if not isinstance(center, list) or len(center) != 3:
        return None

    return [float(center[0]), float(center[1]), float(center[2])]
