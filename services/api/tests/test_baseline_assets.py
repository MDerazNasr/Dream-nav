from json import dumps
from pathlib import Path

from app.baseline_assets import build_nearest_view_baseline_svg


def test_baseline_asset_converts_nearest_pseudo_view_ppm_to_svg(tmp_path: Path) -> None:
    _write_camera_path(tmp_path)
    _write_pseudo_views(tmp_path)
    rgb_path = tmp_path / "pseudo_views" / "rgb" / "train_pose0000_offset00.ppm"
    rgb_path.parent.mkdir(parents=True)
    rgb_path.write_text(
        "P3\n2 1\n255\n10 20 30 40 50 60\n",
        encoding="ascii",
    )

    svg = build_nearest_view_baseline_svg(
        tmp_path,
        _camera_path(),
        nearest_pose_index=0,
    )

    assert 'fill="rgb(10,20,30)"' in svg
    assert 'fill="rgb(40,50,60)"' in svg
    assert "pseudo-view pose 0" in svg


def test_baseline_asset_falls_back_without_pseudo_views(tmp_path: Path) -> None:
    svg = build_nearest_view_baseline_svg(tmp_path, _camera_path(), nearest_pose_index=0)

    assert "nearest view pose 0" in svg


def _write_camera_path(tmp_path: Path) -> None:
    (tmp_path / "camera_path.json").write_text(dumps(_camera_path()), encoding="utf-8")


def _write_pseudo_views(tmp_path: Path) -> None:
    manifest = {
        "views": [
            {
                "view_id": "train_pose0000_offset00",
                "split": "train",
                "source_pose_index": 0,
                "rgb_path": "pseudo_views/rgb/train_pose0000_offset00.ppm",
            }
        ]
    }
    (tmp_path / "pseudo_views.json").write_text(dumps(manifest), encoding="utf-8")


def _camera_path() -> dict[str, object]:
    return {
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
