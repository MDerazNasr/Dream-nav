from json import dumps
from pathlib import Path

from app.point_cloud_to_splat import write_splat_from_points
from app.splat_assets import ensure_job_splat_asset
from app.visibility_assets import build_visibility_manifest


def test_visibility_manifest_uses_splat_points_and_camera_poses(tmp_path: Path) -> None:
    camera_path = _camera_path()
    (tmp_path / "camera_path.json").write_text(dumps(camera_path), encoding="utf-8")
    ensure_job_splat_asset(tmp_path)

    manifest = build_visibility_manifest(
        "scene_abc123",
        camera_path,
        tmp_path / "splat.ply",
        {"method": "voxel_visibility_v1", "observed_threshold": 3},
    )

    zones = {cell["zone"] for cell in manifest["cells"]}
    ratio_total = (
        manifest["observed_ratio"]
        + manifest["partial_ratio"]
        + manifest["completion_candidate_ratio"]
        + manifest["unknown_ratio"]
    )
    assert manifest["scene_id"] == "scene_abc123"
    assert manifest["method"] == "voxel_visibility_v1"
    assert manifest["observed_threshold"] == 3
    assert manifest["partial_threshold"] == [1, 2]
    assert len(manifest["cells"]) >= 6
    assert manifest["cells"][0]["cell_id"] == "cell_000"
    assert "observed" in zones
    assert "completion" in zones
    assert 0.99 <= ratio_total <= 1.01


def test_visibility_manifest_uses_adaptive_fallback_for_room_scale_dense_points(tmp_path: Path) -> None:
    camera_path = _camera_path()
    points = [
        {
            "position": [6.0 + (index * 0.04), 1.2, 7.0 + (index * 0.03)],
            "color": [255, 255, 255],
            "scale": 0.02,
        }
        for index in range(128)
    ]
    write_splat_from_points(points, tmp_path / "splat.ply", max_points=128)

    manifest = build_visibility_manifest(
        "scene_abc123",
        camera_path,
        tmp_path / "splat.ply",
        {"method": "voxel_visibility_v1", "observed_threshold": 3},
    )

    assert manifest["method"] == "voxel_visibility_v1_adaptive"
    assert manifest["observed_ratio"] > 0.0
    assert manifest["completion_candidate_ratio"] < 1.0
    assert "adaptive_thresholds" in manifest


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
            {
                "frame_index": 24,
                "timestamp_sec": 0.8,
                "position": [0.1, 1.45, -1.2],
                "rotation_xyzw": [0, 0.08, 0, 0.9968],
                "fov_degrees": 60,
            },
        ],
    }
