#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from sys import argv, exit

DEFAULT_SCALE = 0.035
MAX_POINTS = 12000

try:
    from .point_cloud_to_splat import PointCloudToSplatError, write_splat_from_points
except ImportError:
    from point_cloud_to_splat import PointCloudToSplatError, write_splat_from_points


class ColmapSparseToSplatError(Exception):
    pass


def build_splat_from_colmap_points(artifacts_root: Path, output_splat: Path, max_points: int = MAX_POINTS) -> int:
    points = _read_points3d(_points3d_path(artifacts_root))
    if not points:
        raise ColmapSparseToSplatError("COLMAP points3D.txt did not contain usable sparse points.")

    try:
        return write_splat_from_points(points, output_splat, max_points=max_points)
    except PointCloudToSplatError as error:
        raise ColmapSparseToSplatError(str(error)) from error


def _points3d_path(artifacts_root: Path) -> Path:
    candidates = [
        artifacts_root / "points3D.txt",
        artifacts_root / "colmap" / "points3D.txt",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return candidates[0]


def _read_points3d(points_path: Path) -> list[dict[str, object]]:
    try:
        lines = points_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ColmapSparseToSplatError("COLMAP points3D.txt is missing.") from error

    points = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split()
        if len(parts) < 8:
            continue

        try:
            x, y, z = (float(parts[1]), float(parts[2]), float(parts[3]))
            r, g, b = (int(parts[4]), int(parts[5]), int(parts[6]))
            error_value = float(parts[7])
        except ValueError:
            continue

        points.append(
            {
                "position": [x, y, z],
                "color": [r, g, b],
                "scale": _point_scale(error_value),
            }
        )

    return points

def _point_scale(error_value: float) -> float:
    if error_value <= 0:
        return DEFAULT_SCALE

    return max(0.015, min(0.08, error_value * 0.025))


def main(args: list[str]) -> int:
    try:
        parsed = _parse_args(args)
        vertex_count = build_splat_from_colmap_points(
            Path(parsed["artifacts_root"]),
            Path(parsed["output_splat"]),
        )
    except ColmapSparseToSplatError as error:
        print(str(error))
        return 1

    print(f"generated_sparse_splat vertices={vertex_count}")
    return 0


def _parse_args(args: list[str]) -> dict[str, str]:
    if len(args) not in {8, 10}:
        raise SystemExit(
            "Usage: colmap_sparse_to_splat.py --artifacts-root <path> --frames-root <path> --camera-path <path> --output-splat <path> [--colmap-command <cmd>]"
        )

    parsed = dict(zip(args[::2], args[1::2], strict=True))
    required = {"--artifacts-root", "--frames-root", "--camera-path", "--output-splat"}
    allowed = required | {"--colmap-command"}
    if not required.issubset(parsed) or not set(parsed).issubset(allowed):
        raise SystemExit(
            "Usage: colmap_sparse_to_splat.py --artifacts-root <path> --frames-root <path> --camera-path <path> --output-splat <path> [--colmap-command <cmd>]"
        )

    return {
        "artifacts_root": parsed["--artifacts-root"],
        "output_splat": parsed["--output-splat"],
    }


if __name__ == "__main__":
    exit(main(argv[1:]))
