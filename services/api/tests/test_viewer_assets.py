from json import dumps, loads
from pathlib import Path

from app.splat_assets import ensure_job_splat_asset
from app.viewer_assets import build_job_viewer_assets


def test_viewer_assets_write_cached_completion_outputs(tmp_path: Path) -> None:
    _write_viewer_inputs(tmp_path, quality_gate="warning")

    summary = build_job_viewer_assets("scene_abc123", "walkthrough.mp4", tmp_path)

    completion = _read_json(tmp_path / "completion_manifest.json")
    quality = _read_json(tmp_path / "quality.json")
    metadata = _read_json(tmp_path / "metadata.json")
    assert completion["cache_strategy"] == "planned_path"
    assert completion["cached_predictions"][0]["rgb_asset"] == "completion/pred_001.svg"
    assert completion["cached_predictions"][0]["confidence_mask_asset"] == "completion/pred_001_mask.svg"
    assert quality["cached_completion"] is True
    assert quality["completion_latency_ms_p50"] == 12
    assert metadata["optimization"]["cached_output_latency_ms_p50"] == 12
    assert (tmp_path / "completion" / "pred_001.svg").is_file()
    assert (tmp_path / "completion" / "pred_001_mask.svg").is_file()
    assert "completion/pred_001.svg" in summary["viewer_assets"]


def test_viewer_assets_disable_cached_completion_on_failed_quality_gate(tmp_path: Path) -> None:
    _write_viewer_inputs(tmp_path, quality_gate="fail")

    summary = build_job_viewer_assets("scene_abc123", "walkthrough.mp4", tmp_path)

    completion = _read_json(tmp_path / "completion_manifest.json")
    quality = _read_json(tmp_path / "quality.json")
    assert completion["model_enabled"] is False
    assert completion["cache_strategy"] == "none"
    assert completion["cached_predictions"] == []
    assert quality["cached_completion"] is False
    assert quality["completion_latency_ms_p50"] is None
    assert not (tmp_path / "completion" / "pred_001.svg").exists()
    assert "completion/pred_001.svg" not in summary["viewer_assets"]


def _write_viewer_inputs(artifacts_root: Path, quality_gate: str) -> None:
    (artifacts_root / "camera_path.json").write_text(dumps(_camera_path()), encoding="utf-8")
    ensure_job_splat_asset(artifacts_root)
    payloads = {
        "capture_quality.json": {"duration_sec": 4.2, "warnings": []},
        "frame_extraction.json": {"frame_count": 3},
        "camera_motion.json": {"backend": "stub"},
        "gaussian_scene.json": {"splat_file": "splat.ply"},
        "visibility_support.json": {"method": "voxel_visibility_v1", "observed_threshold": 3},
        "training_views.json": {"train_views": 2, "heldout_views": 1},
        "scene_model.json": {
            "architecture": "pose_conditioned_encoder_decoder_stub",
            "training_time_sec": 184,
        },
        "heldout_evaluation.json": {"heldout_psnr_median": 21.4},
        "quality_gate.json": {"quality_gate": quality_gate},
    }
    for file_name, payload in payloads.items():
        (artifacts_root / file_name).write_text(dumps(payload), encoding="utf-8")


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


def _read_json(path: Path) -> dict[str, object]:
    return loads(path.read_text(encoding="utf-8"))
