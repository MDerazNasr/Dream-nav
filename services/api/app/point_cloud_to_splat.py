from __future__ import annotations

from math import dist, log
from struct import Struct
from typing import BinaryIO

SH_C0 = 0.28209479177387814
DEFAULT_DENSE_SCALE = 0.018

_PLY_TYPES = {
    "char": ("b", 1),
    "uchar": ("B", 1),
    "int8": ("b", 1),
    "uint8": ("B", 1),
    "short": ("h", 2),
    "ushort": ("H", 2),
    "int16": ("h", 2),
    "uint16": ("H", 2),
    "int": ("i", 4),
    "uint": ("I", 4),
    "int32": ("i", 4),
    "uint32": ("I", 4),
    "float": ("f", 4),
    "float32": ("f", 4),
    "double": ("d", 8),
    "float64": ("d", 8),
}


class PointCloudToSplatError(Exception):
    pass


def write_splat_from_points(
    points: list[dict[str, object]],
    output_splat,
    max_points: int,
) -> int:
    sampled_points = _apply_adaptive_scales(sample_points(points, max_points))
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


def sample_points(points: list[dict[str, object]], max_points: int) -> list[dict[str, object]]:
    if not points:
        raise PointCloudToSplatError("Point cloud did not contain usable points.")

    if len(points) <= max_points:
        return points

    stride = max(1, len(points) // max_points)
    sampled = points[::stride][:max_points]
    if not sampled:
        raise PointCloudToSplatError("Point cloud could not be sampled.")

    return sampled


def _apply_adaptive_scales(points: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(points) < 2 or not _uniform_default_scales(points):
        return points

    nearest_distances = _nearest_neighbor_distances(points)
    scaled_points = []
    for index, point in enumerate(points):
        adaptive_scale = max(DEFAULT_DENSE_SCALE, min(0.12, nearest_distances[index] * 0.65))
        scaled_points.append(
            {
                "position": point["position"],
                "color": point["color"],
                "scale": adaptive_scale,
            }
        )

    return scaled_points


def _uniform_default_scales(points: list[dict[str, object]]) -> bool:
    return all(abs(float(point.get("scale", DEFAULT_DENSE_SCALE)) - DEFAULT_DENSE_SCALE) < 1e-6 for point in points)


def _nearest_neighbor_distances(points: list[dict[str, object]]) -> list[float]:
    neighbor_span = min(12, max(4, len(points) // 2000 + 4))
    axis_orders = [sorted(range(len(points)), key=lambda index: float(points[index]["position"][axis])) for axis in range(3)]
    axis_ranks = [[0] * len(points) for _ in range(3)]
    for axis, order in enumerate(axis_orders):
        for rank, index in enumerate(order):
            axis_ranks[axis][index] = rank

    nearest = [float("inf")] * len(points)
    for index, point in enumerate(points):
        candidates: set[int] = set()
        for axis, order in enumerate(axis_orders):
            rank = axis_ranks[axis][index]
            start = max(0, rank - neighbor_span)
            stop = min(len(order), rank + neighbor_span + 1)
            candidates.update(order[start:stop])

        candidates.discard(index)
        position = point["position"]
        if not isinstance(position, list) or len(position) != 3:
            nearest[index] = DEFAULT_DENSE_SCALE
            continue

        if candidates:
            nearest[index] = min(
                dist(position, points[candidate]["position"])
                for candidate in candidates
                if isinstance(points[candidate]["position"], list) and len(points[candidate]["position"]) == 3
            )
        else:
            nearest[index] = DEFAULT_DENSE_SCALE

        if nearest[index] == float("inf"):
            nearest[index] = DEFAULT_DENSE_SCALE

    return nearest


def read_ply_points(ply_path, default_scale: float = DEFAULT_DENSE_SCALE) -> list[dict[str, object]]:
    with ply_path.open("rb") as payload:
        format_name, vertex_count, properties, header_end = _parse_ply_header(payload)
        payload.seek(header_end)

        if format_name == "ascii":
            return _read_ascii_points(payload, vertex_count, properties, default_scale)

        if format_name == "binary_little_endian":
            return _read_binary_points(payload, vertex_count, properties, default_scale)

    raise PointCloudToSplatError(f"Unsupported PLY format: {format_name}")


def _parse_ply_header(payload: BinaryIO) -> tuple[str, int, list[tuple[str, str]], int]:
    magic = payload.readline().decode("utf-8", errors="replace").strip()
    if magic != "ply":
        raise PointCloudToSplatError("Point cloud PLY header is invalid.")

    format_name = ""
    vertex_count = 0
    properties: list[tuple[str, str]] = []
    in_vertex_element = False

    while True:
        position = payload.tell()
        line = payload.readline()
        if not line:
            raise PointCloudToSplatError("Point cloud PLY header did not terminate.")

        decoded = line.decode("utf-8", errors="replace").strip()
        if decoded == "end_header":
            return format_name, vertex_count, properties, payload.tell()

        if not decoded or decoded.startswith("comment"):
            continue

        parts = decoded.split()
        if parts[0] == "format" and len(parts) >= 2:
            format_name = parts[1]
            continue

        if parts[0] == "element" and len(parts) >= 3:
            in_vertex_element = parts[1] == "vertex"
            if in_vertex_element:
                try:
                    vertex_count = int(parts[2])
                except ValueError as error:
                    raise PointCloudToSplatError("PLY vertex count is invalid.") from error
            continue

        if parts[0] == "property" and in_vertex_element:
            if len(parts) == 5 and parts[1] == "list":
                raise PointCloudToSplatError("PLY vertex list properties are not supported.")
            if len(parts) < 3:
                raise PointCloudToSplatError("PLY property row is malformed.")
            properties.append((parts[1], parts[2]))
            continue

        if parts[0] == "element":
            in_vertex_element = False


def _read_ascii_points(
    payload: BinaryIO,
    vertex_count: int,
    properties: list[tuple[str, str]],
    default_scale: float,
) -> list[dict[str, object]]:
    points = []
    for _ in range(vertex_count):
        line = payload.readline().decode("utf-8", errors="replace").strip()
        if not line:
            continue
        values = line.split()
        if len(values) < len(properties):
            continue
        point = _point_from_values(values, properties, default_scale)
        if point is not None:
            points.append(point)
    return points


def _read_binary_points(
    payload: BinaryIO,
    vertex_count: int,
    properties: list[tuple[str, str]],
    default_scale: float,
) -> list[dict[str, object]]:
    format_codes = []
    row_size = 0
    for property_type, _property_name in properties:
        if property_type not in _PLY_TYPES:
            raise PointCloudToSplatError(f"Unsupported PLY property type: {property_type}")
        format_code, size = _PLY_TYPES[property_type]
        format_codes.append(format_code)
        row_size += size

    struct = Struct("<" + "".join(format_codes))
    points = []
    for _ in range(vertex_count):
        row = payload.read(row_size)
        if len(row) != row_size:
            raise PointCloudToSplatError("PLY binary payload ended before all vertices were read.")
        values = [*struct.unpack(row)]
        point = _point_from_values(values, properties, default_scale)
        if point is not None:
            points.append(point)
    return points


def _point_from_values(values, properties: list[tuple[str, str]], default_scale: float) -> dict[str, object] | None:
    property_map = {name: values[index] for index, (_type_name, name) in enumerate(properties)}
    try:
        x = float(property_map["x"])
        y = float(property_map["y"])
        z = float(property_map["z"])
    except (KeyError, TypeError, ValueError):
        return None

    red = _color_value(property_map.get("red", property_map.get("r", 255)))
    green = _color_value(property_map.get("green", property_map.get("g", 255)))
    blue = _color_value(property_map.get("blue", property_map.get("b", 255)))

    return {
        "position": [x, y, z],
        "color": [red, green, blue],
        "scale": default_scale,
    }


def _color_value(value: object) -> int:
    if isinstance(value, bool):
        return 255

    if isinstance(value, (int, float)):
        return max(0, min(255, int(value)))

    return 255


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
    return Struct("<14f").pack(*values)


def _rgb_channel_to_sh(channel: int) -> float:
    rgb = max(0, min(255, channel)) / 255
    return (rgb - 0.5) / SH_C0
