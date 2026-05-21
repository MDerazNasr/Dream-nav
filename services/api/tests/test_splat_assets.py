from json import dumps
from pathlib import Path
from math import isclose, sqrt
from struct import pack, unpack

from app.splat_assets import ensure_job_splat_asset, import_job_splat_asset, read_splat_points


def test_splat_asset_generator_writes_browser_ply(tmp_path: Path) -> None:
    _write_camera_path(tmp_path)

    summary = ensure_job_splat_asset(tmp_path)

    payload = (tmp_path / "splat.ply").read_bytes()
    assert summary.file_name == "splat.ply"
    assert summary.gaussian_count == 6
    assert summary.source == "stub"
    assert payload.startswith(b"ply\nformat binary_little_endian 1.0")
    assert b"element vertex 6" in payload.split(b"end_header\n", 1)[0]


def test_splat_asset_generator_keeps_existing_splat(tmp_path: Path) -> None:
    _write_camera_path(tmp_path)
    existing_splat = b"ply\nformat ascii 1.0\nelement vertex 1\nend_header\n"
    (tmp_path / "splat.ply").write_bytes(existing_splat)

    summary = ensure_job_splat_asset(tmp_path)

    assert summary.source == "existing"
    assert summary.gaussian_count == 1
    assert (tmp_path / "splat.ply").read_bytes() == existing_splat


def test_import_job_splat_asset_converts_point_cloud_ply(tmp_path: Path) -> None:
    _write_camera_path(tmp_path)
    payload = (
        "ply\n"
        "format ascii 1.0\n"
        "element vertex 3\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
        "0 1 -2 255 0 0\n"
        "0.4 1.1 -2.2 0 255 64\n"
        "0.8 1.3 -2.6 0 32 255\n"
    ).encode("utf-8")

    summary = import_job_splat_asset(tmp_path, "dense_scene.ply", payload)

    assert summary.import_format == "point_cloud_ply"
    assert summary.gaussian_count == 3
    assert summary.source_file == "imports/dense_scene.ply"
    assert (tmp_path / "splat.ply").read_bytes().startswith(b"ply\nformat binary_little_endian 1.0")


def test_import_job_splat_asset_crops_far_outliers_to_camera_bounds(tmp_path: Path) -> None:
    _write_camera_path(tmp_path)
    payload = (
        "ply\n"
        "format ascii 1.0\n"
        "element vertex 3\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
        "0 1.5 0 255 0 0\n"
        "0.4 1.4 -1.0 0 255 64\n"
        "-40 10 25 0 32 255\n"
    ).encode("utf-8")

    summary = import_job_splat_asset(tmp_path, "dense_scene.ply", payload)

    assert summary.import_format == "point_cloud_ply"
    assert summary.gaussian_count == 2


def test_import_job_splat_asset_keeps_imported_splat(tmp_path: Path) -> None:
    imported_splat = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "element vertex 1\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property float f_dc_0\n"
        "property float f_dc_1\n"
        "property float f_dc_2\n"
        "property float opacity\n"
        "property float scale_0\n"
        "property float scale_1\n"
        "property float scale_2\n"
        "property float rot_0\n"
        "property float rot_1\n"
        "property float rot_2\n"
        "property float rot_3\n"
        "end_header\n"
    ).encode("utf-8") + (b"\x00" * (14 * 4))

    summary = import_job_splat_asset(tmp_path, "dense_scene.ply", imported_splat)

    assert summary.import_format == "splat_ply"
    assert summary.gaussian_count == 1
    assert (tmp_path / "splat.ply").read_bytes() == imported_splat


def test_import_job_splat_asset_transforms_nerfstudio_splats_into_viewer_coordinates(tmp_path: Path) -> None:
    imported_splat = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "element vertex 1\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property float f_dc_0\n"
        "property float f_dc_1\n"
        "property float f_dc_2\n"
        "property float opacity\n"
        "property float scale_0\n"
        "property float scale_1\n"
        "property float scale_2\n"
        "property float rot_0\n"
        "property float rot_1\n"
        "property float rot_2\n"
        "property float rot_3\n"
        "end_header\n"
    ).encode("utf-8") + pack(
        "<14f",
        1.0,
        2.0,
        3.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    )

    summary = import_job_splat_asset(
        tmp_path,
        "dense_scene.ply",
        imported_splat,
        source_coordinate_system="nerfstudio_colmap_v1",
    )

    assert summary.import_format == "splat_ply"
    body = (tmp_path / "splat.ply").read_bytes().split(b"end_header\n", 1)[1]
    values = unpack("<14f", body[: 14 * 4])
    assert values[:3] == (1.0, -3.0, 2.0)
    half_sqrt = sqrt(0.5)
    assert isclose(values[10], half_sqrt, rel_tol=1e-6)
    assert isclose(values[11], 0.0, abs_tol=1e-6)
    assert isclose(values[12], 0.0, abs_tol=1e-6)
    assert isclose(values[13], half_sqrt, rel_tol=1e-6)


def test_read_splat_points_samples_across_large_splats(tmp_path: Path) -> None:
    splat_path = tmp_path / "splat.ply"
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "element vertex 4\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property float f_dc_0\n"
        "property float f_dc_1\n"
        "property float f_dc_2\n"
        "property float opacity\n"
        "property float scale_0\n"
        "property float scale_1\n"
        "property float scale_2\n"
        "property float rot_0\n"
        "property float rot_1\n"
        "property float rot_2\n"
        "property float rot_3\n"
        "end_header\n"
    ).encode("utf-8")
    rows = [
        pack("<14f", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        pack("<14f", 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        pack("<14f", 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        pack("<14f", 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
    ]
    splat_path.write_bytes(header + b"".join(rows))

    points = read_splat_points(splat_path, max_points=2)

    assert len(points) == 2
    assert [point.x for point in points] == [0.0, 2.0]


def _write_camera_path(tmp_path: Path) -> None:
    (tmp_path / "camera_path.json").write_text(
        dumps(
            {
                "scene_id": "scene_abc123",
                "coordinate_system": "dreamnav_viewer_v1",
                "intrinsics": {
                    "width": 1280,
                    "height": 720,
                    "fx": 910,
                    "fy": 910,
                    "cx": 640,
                    "cy": 360,
                },
                "poses": [
                    {
                        "frame_index": 0,
                        "timestamp_sec": 0,
                        "position": [0, 1.55, 0],
                        "rotation_xyzw": [0, 0, 0, 1],
                        "fov_degrees": 60,
                    },
                    {
                        "frame_index": 12,
                        "timestamp_sec": 0.4,
                        "position": [0.2, 1.55, -0.6],
                        "rotation_xyzw": [0, 0.03, 0, 0.9995],
                        "fov_degrees": 60,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
