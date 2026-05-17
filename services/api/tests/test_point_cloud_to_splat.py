from math import exp
from struct import Struct
from pathlib import Path

from app.point_cloud_to_splat import DEFAULT_DENSE_SCALE, sample_points, write_splat_from_points


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


def test_write_splat_from_points_uses_normals_for_surfel_orientation(tmp_path: Path) -> None:
    output_path = tmp_path / "splat.ply"
    points = [
        {
            "position": [0.0, 0.0, 0.0],
            "color": [255, 255, 255],
            "scale": DEFAULT_DENSE_SCALE,
            "normal": [1.0, 0.0, 0.0],
        },
        {
            "position": [0.05, 0.0, 0.0],
            "color": [255, 255, 255],
            "scale": DEFAULT_DENSE_SCALE,
            "normal": [1.0, 0.0, 0.0],
        },
    ]

    write_splat_from_points(points, output_path, max_points=16)

    rows = _read_splat_rows(output_path)
    tangent_scale = exp(rows[0][7])
    normal_scale = exp(rows[0][9])

    assert len(rows) == 2
    assert tangent_scale > normal_scale
    assert rows[0][6] < 4.0
    assert abs(rows[0][11]) > 0.6
    assert rows[0][13] > 0.6


def test_sample_points_preserves_sparse_spatial_regions() -> None:
    points = [
        {"position": [index * 0.001, 0.0, 0.0], "color": [255, 255, 255], "scale": DEFAULT_DENSE_SCALE}
        for index in range(1000)
    ] + [
        {"position": [100.0 + index * 0.001, 0.0, 0.0], "color": [255, 0, 0], "scale": DEFAULT_DENSE_SCALE}
        for index in range(10)
    ]

    sampled = sample_points(points, 10)
    sampled_x = sorted(point["position"][0] for point in sampled)

    assert len(sampled) == 10
    assert sampled_x[0] < 1
    assert sampled_x[-1] >= 100


def test_sample_points_thins_voxel_representatives_evenly() -> None:
    points = [
        {"position": [float(index), 0.0, 0.0], "color": [255, 255, 255], "scale": DEFAULT_DENSE_SCALE}
        for index in range(100)
    ]

    sampled = sample_points(points, 10)
    sampled_x = [point["position"][0] for point in sampled]

    assert len(sampled) == 10
    assert sampled_x[0] == 0.0
    assert sampled_x[-1] >= 90.0


def test_read_ply_points_preserves_normals(tmp_path: Path) -> None:
    from app.point_cloud_to_splat import read_ply_points

    ply_path = tmp_path / "dense.ply"
    ply_path.write_text(
        "ply\n"
        "format ascii 1.0\n"
        "element vertex 1\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property float nx\n"
        "property float ny\n"
        "property float nz\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
        "0 1 -2 1 0 0 255 0 0\n",
        encoding="utf-8",
    )

    points = read_ply_points(ply_path)

    assert points[0]["normal"] == [1.0, 0.0, 0.0]


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
