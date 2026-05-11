from json import dumps, loads
from pathlib import Path

from app.pseudo_views import render_pseudo_views
from app.splat_assets import ensure_job_splat_asset


def test_pseudo_view_renderer_writes_manifest_rgb_and_depth(tmp_path: Path) -> None:
    camera_path = _camera_path()
    (tmp_path / "camera_path.json").write_text(dumps(camera_path), encoding="utf-8")
    ensure_job_splat_asset(tmp_path)

    summary = render_pseudo_views("scene_abc123", "walkthrough.mp4", tmp_path)
    manifest = loads((tmp_path / "pseudo_views.json").read_text(encoding="utf-8"))
    first_view = manifest["views"][0]

    assert summary["pseudo_views_manifest"] == "pseudo_views.json"
    assert summary["train_views"] == 6
    assert summary["heldout_views"] == 2
    assert manifest["renderer"] == "placeholder_splat_renderer_v1"
    assert manifest["split_strategy"] == "camera_path_perturbation_v1"
    assert manifest["depth_source"] == "splat_depth_placeholder_v1"
    assert manifest["rgb_size"] == [8, 6]
    assert first_view["split"] == "train"
    assert first_view["target_pose"]["position"] == [0, 1.55, 0]
    assert (tmp_path / first_view["rgb_path"]).read_text(encoding="ascii").startswith("P3\n8 6\n255")
    assert (tmp_path / first_view["depth_path"]).read_text(encoding="ascii").startswith("P2\n8 6\n65535")


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
