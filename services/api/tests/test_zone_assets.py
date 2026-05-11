from app.zone_assets import ZONE_FILE_NAMES, build_zone_artifacts


def test_zone_artifacts_split_visibility_cells_by_zone() -> None:
    artifacts = build_zone_artifacts(
        "scene_abc123",
        {
            "scene_id": "scene_abc123",
            "cells": [
                _cell("cell_001", [0, 1, 0], 4, "observed"),
                _cell("cell_002", [0.5, 1, -0.5], 1, "partial"),
                _cell("cell_003", [1, 1, -1], 0, "completion"),
            ],
        },
    )

    assert set(artifacts) == set(ZONE_FILE_NAMES)
    assert artifacts["observed_zone.json"]["cell_count"] == 1
    assert artifacts["observed_zone.json"]["coverage_ratio"] == 0.3333
    assert artifacts["observed_zone.json"]["bounds"] == {"min": [0, 1, 0], "max": [0, 1, 0]}
    assert artifacts["partial_zone.json"]["cells"][0]["cell_id"] == "cell_002"
    assert artifacts["completion_zone.json"]["zone"] == "completion"
    assert artifacts["unknown_zone.json"]["cell_count"] == 0
    assert artifacts["unknown_zone.json"]["bounds"] is None


def _cell(cell_id: str, center: list[float], visibility_count: int, zone: str) -> dict[str, object]:
    return {
        "cell_id": cell_id,
        "center": center,
        "size_meters": 0.5,
        "visibility_count": visibility_count,
        "zone": zone,
    }
