from math import exp
from struct import Struct
from pathlib import Path

from app.point_cloud_to_splat import DEFAULT_DENSE_SCALE, write_splat_from_points


def test_write_splat_from_points_adapts_sparse_point_scales(tmp_path: Path) -> None:
    output_path = tmp_path / "splat.ply"

    write_splat_from_points(
        [
            {"position": [0.0, 0.0, 0.0], "color": [255, 128, 64], "scale": DEFAULT_DENSE_SCALE},
            {"position": [0.5, 0.0, 0.0], "color": [255, 128, 64], "scale": DEFAULT_DENSE_SCALE},
        ],
        output_path,
        max_points=16,
    )

    rows = _read_splat_rows(output_path)

    assert len(rows) == 2
    assert exp(rows[0][7]) > DEFAULT_DENSE_SCALE
    assert exp(rows[1][7]) > DEFAULT_DENSE_SCALE


def test_write_splat_from_points_preserves_explicit_scales(tmp_path: Path) -> None:
    output_path = tmp_path / "splat.ply"

    write_splat_from_points(
        [
            {"position": [0.0, 0.0, 0.0], "color": [255, 255, 255], "scale": 0.04},
            {"position": [0.05, 0.0, 0.0], "color": [255, 255, 255], "scale": 0.04},
        ],
        output_path,
        max_points=16,
    )

    rows = _read_splat_rows(output_path)

    assert len(rows) == 2
    assert abs(exp(rows[0][7]) - 0.04) < 1e-6
    assert abs(exp(rows[1][7]) - 0.04) < 1e-6


def test_write_splat_from_points_caps_dense_cloud_scales(tmp_path: Path) -> None:
    output_path = tmp_path / "splat.ply"
    points = [
        {"position": [index * 0.05, 0.0, 0.0], "color": [255, 255, 255], "scale": DEFAULT_DENSE_SCALE}
        for index in range(12)
    ]

    write_splat_from_points(points, output_path, max_points=32)

    rows = _read_splat_rows(output_path)
    recovered_scales = [exp(row[7]) for row in rows]

    assert len(rows) == 12
    assert max(recovered_scales) <= 0.05 + 1e-6


def _read_splat_rows(path: Path) -> list[tuple[float, ...]]:
    with path.open("rb") as payload:
        vertex_count = 0
        while True:
            line = payload.readline()
            if not line:
                raise RuntimeError("Missing PLY header terminator")
            decoded = line.decode("utf-8", errors="replace").strip()
            if decoded.startswith("element vertex "):
                vertex_count = int(decoded.split()[-1])
            if decoded == "end_header":
                break

        row_struct = Struct("<14f")
        return [row_struct.unpack(payload.read(row_struct.size)) for _ in range(vertex_count)]
