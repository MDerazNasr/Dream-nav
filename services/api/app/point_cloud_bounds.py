from __future__ import annotations

from json import JSONDecodeError, loads
from pathlib import Path


def filter_points_to_camera_bounds(
    points: list[dict[str, object]],
    camera_path_path: Path,
) -> list[dict[str, object]]:
    poses = _supported_camera_positions(camera_path_path)
    if not poses:
        return points

    mins = [min(pose[axis] for pose in poses) for axis in range(3)]
    maxs = [max(pose[axis] for pose in poses) for axis in range(3)]
    margins = [_camera_margin(maxs[axis] - mins[axis]) for axis in range(3)]
    filtered = [
        point
        for point in points
        if _point_within_bounds(point.get("position"), mins, maxs, margins)
    ]

    minimum_retained = max(1, len(points) // 3) if len(points) < 1000 else max(5000, len(points) // 2)
    return filtered if len(filtered) >= minimum_retained else points


def _point_within_bounds(
    position: object,
    mins: list[float],
    maxs: list[float],
    margins: list[float],
) -> bool:
    if not isinstance(position, list) or len(position) != 3:
        return False

    return all(
        mins[axis] - margins[axis] <= float(position[axis]) <= maxs[axis] + margins[axis]
        for axis in range(3)
    )


def _supported_camera_positions(camera_path_path: Path) -> list[tuple[float, float, float]]:
    try:
        payload = loads(camera_path_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except JSONDecodeError:
        return []

    poses = payload.get("poses")
    if not isinstance(poses, list):
        return []

    positions = [
        (float(position[0]), float(position[1]), float(position[2]))
        for pose in poses
        if isinstance(pose, dict)
        and isinstance((position := pose.get("position")), list)
        and len(position) == 3
    ]
    if len(positions) < 8:
        return positions

    percentile_mins = [_percentile([pose[axis] for pose in positions], 0.1) for axis in range(3)]
    percentile_maxs = [_percentile([pose[axis] for pose in positions], 0.9) for axis in range(3)]
    margins = [max(0.35, (percentile_maxs[axis] - percentile_mins[axis]) * 0.5) for axis in range(3)]
    filtered = [
        pose
        for pose in positions
        if all(
            percentile_mins[axis] - margins[axis] <= pose[axis] <= percentile_maxs[axis] + margins[axis]
            for axis in range(3)
        )
    ]
    minimum_supported_count = max(4, len(positions) // 3)
    return filtered if len(filtered) >= minimum_supported_count else positions


def _camera_margin(span: float) -> float:
    return max(2.5, min(8.0, (span * 0.5) + 1.5))


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * quantile)))
    return ordered[index]
