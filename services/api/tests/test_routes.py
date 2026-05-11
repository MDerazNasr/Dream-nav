from pathlib import Path

from fastapi.testclient import TestClient

from app.config import ApiSettings
from app.main import create_app


def test_health_returns_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "dreamnav-api"}


def test_demo_scenes_returns_locked_scene() -> None:
    client = TestClient(create_app())

    response = client.get("/demo-scenes")

    assert response.status_code == 200
    assert response.json()[0]["scene_id"] == "warehouse_01"


def test_scene_assets_match_spec_urls() -> None:
    client = TestClient(create_app())

    response = client.get("/scene/warehouse_01")

    assert response.status_code == 200
    assert response.json()["splat_url"] == "/scenes/warehouse_01/splat.ply"


def test_quality_returns_scene_metrics() -> None:
    client = TestClient(create_app())

    response = client.get("/quality/warehouse_01")

    assert response.status_code == 200
    assert response.json()["runtime_path"] == "torch_fp16"


def test_asset_status_reports_splat_mode_when_splat_exists() -> None:
    client = TestClient(create_app())

    response = client.get("/scene/warehouse_01/asset-status")

    assert response.status_code == 200
    assert response.json()["viewer_render_mode"] == "splat"
    assert response.json()["missing_assets"] == []


def test_missing_scene_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/scene/missing_scene")

    assert response.status_code == 404
    assert response.json()["detail"] == "Scene not found"


def test_missing_quality_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/quality/missing_scene")

    assert response.status_code == 404
    assert response.json()["detail"] == "Scene not found"


def test_static_scene_metadata_is_served() -> None:
    client = TestClient(create_app())

    response = client.get("/scenes/warehouse_01/metadata.json")

    assert response.status_code == 200
    assert response.json()["scene_id"] == "warehouse_01"


def test_upload_creates_processing_job(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))

    response = client.post(
        "/upload",
        files={"file": ("walkthrough.mp4", b"video-bytes", "video/mp4")},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["job_id"].startswith("scene_")
    assert payload["validation_status"] == "pass"
    assert payload["warnings"] == []
    assert (tmp_path / "data" / "uploads" / payload["job_id"] / "walkthrough.mp4").is_file()


def test_upload_warns_for_unsupported_video_extension(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))

    response = client.post(
        "/upload",
        files={"file": ("walkthrough.txt", b"not-video", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["validation_status"] == "warning"
    assert response.json()["warnings"] == [
        "Use MP4, MOV, or M4V walkthrough videos for reconstruction."
    ]


def test_status_returns_processing_progress(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]

    response = client.get(f"/status/{job_id}")

    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    assert response.json()["state"] == "queued"
    assert response.json()["stage"] == "checking_capture_quality"
    assert response.json()["progress"] == 0
    assert response.json()["output_scene_id"] is None
    assert response.json()["failed_stage"] is None
    assert response.json()["failed_artifact"] is None


def test_status_returns_failed_job_state(tmp_path: Path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]
    app.state.job_repository.fail_job(
        job_id,
        "Bad poses break splat",
        failed_stage="estimating_camera_motion",
        failed_artifact="camera_motion_command.json",
    )

    response = client.get(f"/status/{job_id}")

    assert response.status_code == 200
    assert response.json()["state"] == "failed"
    assert response.json()["stage"] == "failed"
    assert response.json()["error_message"] == "Bad poses break splat"
    assert response.json()["failed_stage"] == "estimating_camera_motion"
    assert response.json()["failed_artifact"] == "camera_motion_command.json"


def test_job_artifact_returns_job_scoped_json(tmp_path: Path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]
    app.state.job_repository.write_artifact(
        job_id,
        "frame_extraction_command.json",
        {"exit_code": 0, "stdout": "ok"},
    )

    response = client.get(f"/jobs/{job_id}/artifacts/frame_extraction_command.json")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job_id,
        "artifact_name": "frame_extraction_command.json",
        "payload": {"exit_code": 0, "stdout": "ok"},
    }


def test_completed_job_scene_bundle_returns_viewer_assets(tmp_path: Path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]
    _write_viewer_assets(app.state.job_repository, job_id)
    app.state.job_repository.complete_job(job_id, job_id)

    response = client.get(f"/jobs/{job_id}/scene-bundle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job_id
    assert payload["output_scene_id"] == job_id
    assert payload["assets"]["metadata_url"] == f"/jobs/{job_id}/viewer-assets/metadata.json"
    assert payload["metadata"]["scene_id"] == job_id
    assert payload["quality"]["scene_id"] == job_id
    assert payload["camera_path"]["scene_id"] == job_id
    assert payload["visibility"]["scene_id"] == job_id
    assert payload["completion"]["scene_id"] == job_id
    assert payload["asset_status"]["viewer_render_mode"] == "splat"


def test_job_viewer_asset_serves_raw_json(tmp_path: Path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]
    _write_viewer_assets(app.state.job_repository, job_id)

    response = client.get(f"/jobs/{job_id}/viewer-assets/metadata.json")
    splat_response = client.get(f"/jobs/{job_id}/viewer-assets/splat.ply")

    assert response.status_code == 200
    assert response.json()["scene_id"] == job_id
    assert splat_response.status_code == 200
    assert splat_response.content.startswith(b"ply\n")


def test_job_viewer_asset_rejects_unlisted_names(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]

    response = client.get(f"/jobs/{job_id}/viewer-assets/nested/secret.json")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsafe viewer asset name"


def test_job_scene_bundle_waits_for_completed_job(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]

    response = client.get(f"/jobs/{job_id}/scene-bundle")

    assert response.status_code == 409
    assert response.json()["detail"] == "Job explorer bundle is not ready"


def test_job_artifact_rejects_unsafe_names(tmp_path: Path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]

    response = client.get(f"/jobs/{job_id}/artifacts/nested/secret.json")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsafe artifact name"


def test_job_artifact_returns_404_for_missing_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]

    response = client.get(f"/jobs/{job_id}/artifacts/missing.json")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job artifact not found"


def test_missing_job_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/status/scene_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def _write_viewer_assets(job_repository, job_id: str) -> None:
    camera_path = {
        "scene_id": job_id,
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
            }
        ],
    }
    visibility = {
        "scene_id": job_id,
        "method": "voxel_visibility_v1",
        "observed_threshold": 3,
        "partial_threshold": [1, 2],
        "observed_ratio": 0.62,
        "partial_ratio": 0.22,
        "completion_candidate_ratio": 0.11,
        "unknown_ratio": 0.05,
        "cells": [
            {
                "cell_id": "cell_observed_001",
                "center": [0, 1, -0.5],
                "size_meters": 0.5,
                "visibility_count": 5,
                "zone": "observed",
            }
        ],
    }
    completion = {
        "scene_id": job_id,
        "model_enabled": True,
        "architecture": "pose_conditioned_encoder_decoder",
        "quality_gate": "warning",
        "heldout_psnr_median": 21.4,
        "cache_strategy": "none",
        "cached_predictions": [],
    }
    quality = {
        "scene_id": job_id,
        "pose_backend": "stub",
        "frame_count": 1,
        "visibility_threshold_observed": 3,
        "splat_fps": 0,
        "scene_model_training_sec": 184,
        "heldout_psnr_median": 21.4,
        "quality_gate": "warning",
        "completion_latency_ms_p50": None,
        "completion_latency_ms_p95": None,
        "runtime_path": "placeholder",
        "cached_completion": False,
    }
    metadata = {
        "scene_id": job_id,
        "title": "Processed walkthrough",
        "input_video": "walkthrough.mov",
        "duration_sec": 0,
        "frame_count": 1,
        "pose_backend": "stub",
        "camera_path": "camera_path.json",
        "splat_file": "splat.ply",
        "visibility": {
            "observed_threshold": 3,
            "partial_threshold": [1, 2],
            "observed_ratio": 0.62,
            "partial_ratio": 0.22,
            "completion_candidate_ratio": 0.11,
        },
        "scene_model": {
            "enabled": True,
            "architecture": "pose_conditioned_encoder_decoder",
            "train_views": 520,
            "heldout_views": 80,
            "training_time_sec": 184,
            "loss": "L_rgb + lambda_geo * L_geo",
            "heldout_psnr_median": 21.4,
            "quality_gate": "warning",
            "lpips": None,
        },
        "optimization": {
            "fp32_latency_ms_p50": None,
            "fp16_latency_ms_p50": None,
            "compiled_latency_ms_p50": None,
            "tensorrt_latency_ms_p50": None,
            "cached_output_latency_ms_p50": None,
        },
        "zones": {
            "observed": "observed_zone.json",
            "partial": "partial_zone.json",
            "completion": "completion_zone.json",
            "unknown": "unknown_zone.json",
        },
        "quality": {
            "capture_score": 0.92,
            "sharpness_score": 0.79,
            "parallax_score": 0.82,
            "texture_score": 0.8,
            "splat_fps": 0,
            "processing_time_sec": 0,
        },
        "product_tools": {
            "lens_modes": ["24mm", "35mm", "50mm", "85mm"],
            "camera_markers_enabled": True,
            "notes_enabled": False,
        },
    }

    for artifact_name, payload in {
        "camera_path.json": camera_path,
        "metadata.json": metadata,
        "quality.json": quality,
        "visibility_manifest.json": visibility,
        "completion_manifest.json": completion,
    }.items():
        job_repository.write_artifact(job_id, artifact_name, payload)

    splat_path = job_repository.artifact_root(job_id) / "splat.ply"
    splat_path.write_bytes(b"ply\nformat ascii 1.0\nend_header\n")
