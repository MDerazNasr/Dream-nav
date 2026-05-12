#!/usr/bin/env python3

from __future__ import annotations

from math import log
from pathlib import Path
from struct import pack
from sys import argv, exit

SH_C0 = 0.28209479177387814
DEFAULT_SCALE = 0.035
MAX_POINTS = 12000


class ColmapSparseToSplatError(Exception):
    pass


def build_splat_from_colmap_points(artifacts_root: Path, output_splat: Path, max_points: int = MAX_POINTS) -> int:
    points = _read_points3d(_points3d_path(artifacts_root))
    if not points:
        raise ColmapSparseToSplatError("COLMAP points3D.txt did not contain usable sparse points.")

    sampled_points = _sample_points(points, max_points)
    rows = [_pack_splat_row(point["position"], point["color"], point["scale"]) for point in sampled_points]
    header = "\n".join(
        [
            "ply",
            "format binary_little_endian 1.0",
            f"element vertex {len(rows)}",
            "property float x",
            "property float y",
            "property float z",
            "property float f_dc_0",
            "property float f_dc_1",
            "property float f_dc_2",
            "property float opacity",
            "property float scale_0",
            "property float scale_1",
            "property float scale_2",
            "property float rot_0",
            "property float rot_1",
            "property float rot_2",
            "property float rot_3",
            "end_header\n",
        ]
    )
    output_splat.write_bytes(header.encode("utf-8") + b"".join(rows))
    return len(rows)


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


def _sample_points(points: list[dict[str, object]], max_points: int) -> list[dict[str, object]]:
    if len(points) <= max_points:
        return points

    stride = max(1, len(points) // max_points)
    sampled = points[::stride][:max_points]
    if not sampled:
        raise ColmapSparseToSplatError("COLMAP sparse points could not be sampled.")

    return sampled


def _point_scale(error_value: float) -> float:
    if error_value <= 0:
        return DEFAULT_SCALE

    return max(0.015, min(0.08, error_value * 0.025))


def _pack_splat_row(position: list[float], color: list[int], scale: float) -> bytes:
    scale_log = log(scale)
    values = [
        float(position[0]),
        float(position[1]),
        float(position[2]),
        _rgb_channel_to_sh(color[0]),
        _rgb_channel_to_sh(color[1]),
        _rgb_channel_to_sh(color[2]),
        4,
        scale_log,
        scale_log,
        scale_log,
        0,
        0,
        0,
        1,
    ]
    return pack("<14f", *values)


def _rgb_channel_to_sh(channel: int) -> float:
    rgb = max(0, min(255, channel)) / 255
    return (rgb - 0.5) / SH_C0


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
    if len(args) != 8:
        raise SystemExit(
            "Usage: colmap_sparse_to_splat.py --artifacts-root <path> --frames-root <path> --camera-path <path> --output-splat <path>"
        )

    parsed = dict(zip(args[::2], args[1::2], strict=True))
    required = {"--artifacts-root", "--frames-root", "--camera-path", "--output-splat"}
    if set(parsed) != required:
        raise SystemExit(
            "Usage: colmap_sparse_to_splat.py --artifacts-root <path> --frames-root <path> --camera-path <path> --output-splat <path>"
        )

    return {
        "artifacts_root": parsed["--artifacts-root"],
        "output_splat": parsed["--output-splat"],
    }


if __name__ == "__main__":
    exit(main(argv[1:]))
