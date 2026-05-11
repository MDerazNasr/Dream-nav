from json import dumps
from pathlib import Path

from app.splat_assets import ensure_job_splat_asset


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
