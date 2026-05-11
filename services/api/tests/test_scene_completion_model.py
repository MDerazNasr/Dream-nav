from json import dumps, loads
from pathlib import Path

import pytest

from app.completion_dataset import build_completion_dataset
from app.pseudo_views import render_pseudo_views
from app.scene_completion_model import SceneCompletionModelError, train_scene_completion_model
from app.splat_assets import ensure_job_splat_asset


def test_scene_completion_model_writes_weights_from_dataset(tmp_path: Path) -> None:
    _write_camera_path(tmp_path)
    ensure_job_splat_asset(tmp_path)
    render_pseudo_views("scene_abc123", "walkthrough.mp4", tmp_path)
    build_completion_dataset("scene_abc123", "walkthrough.mp4", tmp_path)

    summary = train_scene_completion_model("scene_abc123", "walkthrough.mp4", tmp_path)
    weights = loads((tmp_path / "scene_model_weights.json").read_text(encoding="utf-8"))

    assert summary["model_artifact"] == "scene_model_weights.json"
    assert summary["model_version"] == "scene_completion_mean_rgb_v1"
    assert weights["architecture"] == "pose_conditioned_encoder_decoder_stub"
    assert weights["train_examples"] == 6
    assert weights["heldout_examples"] == 2
    assert len(weights["rgb_channel_mean"]) == 3
    assert len(weights["pose_bias"]) == 8
    assert weights["train_rgb_l1"] >= 0


def test_scene_completion_model_fails_when_dataset_is_missing(tmp_path: Path) -> None:
    with pytest.raises(SceneCompletionModelError, match="Scene model input invalid"):
        train_scene_completion_model("scene_abc123", "walkthrough.mp4", tmp_path)


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
