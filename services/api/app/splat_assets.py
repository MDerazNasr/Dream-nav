from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError, loads
from math import log
from pathlib import Path
from re import sub
from struct import pack, unpack
from typing import Any

from .point_cloud_to_splat import PointCloudToSplatError, read_ply_points, write_splat_from_points

IMPORTED_POINT_CLOUD_MAX_POINTS = 50000
_SPLAT_PROPERTIES = {
    "x",
    "y",
    "z",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
    "rot_0",
    "rot_1",
    "rot_2",
    "rot_3",
}


class SplatAssetError(Exception):
    pass


@dataclass(frozen=True)
class SplatAssetSummary:
    file_name: str
    gaussian_count: int
    source: str
    file_size_bytes: int


@dataclass(frozen=True)
class SplatPoint:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class ImportedSplatAssetSummary:
    source_file: str
    import_format: str
    gaussian_count: int
    file_size_bytes: int


def ensure_job_splat_asset(artifacts_root: Path, allow_stub: bool = True) -> SplatAssetSummary:
    splat_path = artifacts_root / "splat.ply"
    if splat_path.is_file() and splat_path.stat().st_size > 0:
        return _summary(splat_path, "existing")

    if not allow_stub:
        raise SplatAssetError("Gaussian reconstruction did not produce splat.ply.")

    camera_path = _read_camera_path(artifacts_root / "camera_path.json")
    splats = _splats_from_camera_path(camera_path)
    _write_splat_ply(splat_path, splats)
    return _summary(splat_path, "stub")


def import_job_splat_asset(
    artifacts_root: Path,
    source_filename: str,
    payload: bytes,
    max_points: int = IMPORTED_POINT_CLOUD_MAX_POINTS,
) -> ImportedSplatAssetSummary:
    if not payload:
        raise SplatAssetError("Imported Gaussian asset is empty.")

    source_suffix = Path(source_filename).suffix.lower()
    if source_suffix != ".ply":
        raise SplatAssetError("Imported Gaussian asset must be a .ply file.")

    import_root = artifacts_root / "imports"
    import_root.mkdir(parents=True, exist_ok=True)
    source_file = _safe_import_filename(source_filename)
    imported_path = import_root / source_file
    imported_path.write_bytes(payload)

    splat_path = artifacts_root / "splat.ply"
    if _is_splat_ply(imported_path):
        splat_path.write_bytes(payload)
        gaussian_count = _read_vertex_count(splat_path)
        import_format = "splat_ply"
    else:
        try:
            points = read_ply_points(imported_path)
            gaussian_count = write_splat_from_points(points, splat_path, max_points=max_points)
        except PointCloudToSplatError as error:
            raise SplatAssetError(str(error)) from error
        import_format = "point_cloud_ply"

    return ImportedSplatAssetSummary(
        source_file=f"imports/{source_file}",
        import_format=import_format,
        gaussian_count=gaussian_count,
        file_size_bytes=imported_path.stat().st_size,
    )


def _splats_from_camera_path(camera_path: dict[str, Any]) -> list[dict[str, object]]:
    poses = camera_path.get("poses") if isinstance(camera_path.get("poses"), list) else []
    anchor = _pose_position(poses, 0, [0, 1.35, -1.2])
    middle = _pose_position(poses, len(poses) // 2, [0.2, 1.35, -1.55])
    last = _pose_position(poses, len(poses) - 1, [0.1, 1.0, -2.05])
    return [
        {"position": [anchor[0] - 0.35, anchor[1] - 0.2, anchor[2] - 0.7], "color": [1.3, -0.5, -0.5], "scale": 0.18},
        {"position": [anchor[0] + 0.1, anchor[1], anchor[2] - 0.85], "color": [-0.4, 1.1, -0.4], "scale": 0.2},
        {"position": [middle[0], middle[1] - 0.2, middle[2] - 0.55], "color": [-0.5, -0.3, 1.3], "scale": 0.18},
        {"position": [middle[0] + 0.45, middle[1] + 0.05, middle[2] - 0.7], "color": [1.2, 0.7, -0.4], "scale": 0.22},
        {"position": [last[0], last[1] - 0.55, last[2] - 0.5], "color": [0.9, 0.9, 0.9], "scale": 0.26},
        {"position": [last[0] - 0.65, last[1] - 0.65, last[2] - 0.3], "color": [0.4, 1.0, 0.9], "scale": 0.16},
    ]


def _write_splat_ply(path: Path, splats: list[dict[str, object]]) -> None:
    properties = [
        "x",
        "y",
        "z",
        "f_dc_0",
        "f_dc_1",
        "f_dc_2",
        "opacity",
        "scale_0",
        "scale_1",
        "scale_2",
        "rot_0",
        "rot_1",
        "rot_2",
        "rot_3",
    ]
    header = "\n".join(
        [
            "ply",
            "format binary_little_endian 1.0",
            f"element vertex {len(splats)}",
            *(f"property float {property_name}" for property_name in properties),
            "end_header\n",
        ]
    )
    rows = [_pack_splat_row(splat) for splat in splats]
    path.write_bytes(header.encode("utf-8") + b"".join(rows))


def _pack_splat_row(splat: dict[str, object]) -> bytes:
    position = splat["position"]
    color = splat["color"]
    scale = log(float(splat["scale"]))
    if not isinstance(position, list) or not isinstance(color, list):
        raise SplatAssetError("Splat row data is invalid.")

    values = [
        *[float(value) for value in position],
        *[float(value) for value in color],
        4,
        scale,
        scale,
        scale,
        0,
        0,
        0,
        1,
    ]
    return pack("<14f", *values)


def _pose_position(poses: list[object], index: int, fallback: list[float]) -> list[float]:
    if index < 0 or index >= len(poses) or not isinstance(poses[index], dict):
        return fallback

    position = poses[index].get("position")
    if not isinstance(position, list) or len(position) != 3:
        return fallback

    return [float(position[0]), float(position[1]), float(position[2])]


def _read_camera_path(path: Path) -> dict[str, Any]:
    try:
        payload = loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, JSONDecodeError) as error:
        raise SplatAssetError("Camera path is required before building a splat asset.") from error

    if not isinstance(payload, dict):
        raise SplatAssetError("Camera path must be a JSON object.")

    return payload


def _summary(splat_path: Path, source: str) -> SplatAssetSummary:
    return SplatAssetSummary(
        file_name=splat_path.name,
        gaussian_count=_read_vertex_count(splat_path),
        source=source,
        file_size_bytes=splat_path.stat().st_size,
    )


def _read_vertex_count(path: Path) -> int:
    header = path.read_bytes().split(b"end_header\n", 1)[0].decode("utf-8", errors="replace")
    for line in header.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[:2] == ["element", "vertex"]:
            return int(parts[2])

    raise SplatAssetError("Splat PLY missing vertex count.")


def read_splat_points(path: Path, max_points: int = 512) -> list[SplatPoint]:
    payload = path.read_bytes()
    header, _, body = payload.partition(b"end_header\n")
    header_text = header.decode("utf-8", errors="replace")
    vertex_count = _vertex_count_from_header(header_text)
    properties = _properties_from_header(header_text)

    if "format binary_little_endian 1.0" not in header_text:
        raise SplatAssetError("Only binary little-endian splat PLY files are supported for visibility.")

    if len(properties) < 3 or properties[:3] != ["x", "y", "z"]:
        raise SplatAssetError("Splat PLY must start with x, y, z float properties.")

    row_size = len(properties) * 4
    point_count = min(vertex_count, max_points)
    points = []
    for index in range(point_count):
        offset = index * row_size
        if offset + 12 > len(body):
            break

        x, y, z = unpack("<3f", body[offset : offset + 12])
        points.append(SplatPoint(x=x, y=y, z=z))

    if not points:
        raise SplatAssetError("Splat PLY did not contain readable points.")

    return points


def _vertex_count_from_header(header: str) -> int:
    for line in header.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[:2] == ["element", "vertex"]:
            return int(parts[2])

    raise SplatAssetError("Splat PLY missing vertex count.")


def _properties_from_header(header: str) -> list[str]:
    properties = []
    for line in header.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[:2] == ["property", "float"]:
            properties.append(parts[2])

    return properties


def _is_splat_ply(path: Path) -> bool:
    header = path.read_bytes().split(b"end_header\n", 1)[0].decode("utf-8", errors="replace")
    return "format binary_little_endian 1.0" in header and _SPLAT_PROPERTIES.issubset(_properties_from_header(header))


def _safe_import_filename(filename: str) -> str:
    stem = Path(filename).stem or "gaussian_input"
    safe_stem = sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "gaussian_input"
    return f"{safe_stem}.ply"
