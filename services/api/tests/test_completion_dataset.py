from json import dumps, loads
from pathlib import Path

import pytest

from app.completion_dataset import CompletionDatasetError, build_completion_dataset
from app.pseudo_views import render_pseudo_views
from app.splat_assets import ensure_job_splat_asset


def test_completion_dataset_builds_examples_from_pseudo_views(tmp_path: Path) -> None:
    _write_camera_path(tmp_path)
    ensure_job_splat_asset(tmp_path)
    render_pseudo_views("scene_abc123", "walkthrough.mp4", tmp_path)

    summary = build_completion_dataset("scene_abc123", "walkthrough.mp4", tmp_path)
    manifest = loads((tmp_path / "completion_dataset.json").read_text(encoding="utf-8"))
    first_example = manifest["examples"][0]
    heldout_example = next(example for example in manifest["examples"] if example["split"] == "heldout")

    assert summary["dataset_manifest"] == "completion_dataset.json"
    assert summary["train_examples"] == 6
    assert summary["heldout_examples"] == 2
    assert manifest["pose_encoding"] == "position_rotation_fov_v1"
    assert manifest["reference_strategy"] == "nearest_train_views_v1"
    assert first_example["pose_encoding"] == [0, 1.55, 0, 0, 0, 0, 1, 0.33333]
    assert first_example["references"][0]["view_id"] != first_example["example_id"]
    assert heldout_example["references"]


def test_completion_dataset_fails_when_pseudo_view_file_is_missing(tmp_path: Path) -> None:
    _write_camera_path(tmp_path)
    ensure_job_splat_asset(tmp_path)
    render_pseudo_views("scene_abc123", "walkthrough.mp4", tmp_path)
    manifest = loads((tmp_path / "pseudo_views.json").read_text(encoding="utf-8"))
    first_rgb_path = tmp_path / manifest["views"][0]["rgb_path"]
    first_rgb_path.unlink()

    with pytest.raises(CompletionDatasetError, match="Pseudo-view asset missing"):
        build_completion_dataset("scene_abc123", "walkthrough.mp4", tmp_path)


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
