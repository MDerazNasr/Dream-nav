from fastapi.testclient import TestClient

from app.config import ApiSettings
from app.main import create_app


def test_import_gaussian_route_converts_point_cloud_for_completed_job(tmp_path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    job_id = _completed_job(client, app)

    response = client.post(
        f"/jobs/{job_id}/import-gaussian",
        files={"file": ("dense_scene.ply", _point_cloud_ply(3), "application/octet-stream")},
    )

    assert response.status_code == 200
    assert response.json()["import_format"] == "point_cloud_ply"
    assert response.json()["gaussian_count"] == 3
    assert response.json()["viewer_render_mode"] == "splat"
    assert response.json()["featured_candidate"] is False
    assert (app.state.job_repository.artifact_root(job_id) / "splat.ply").is_file()
    gaussian_scene = app.state.job_repository.read_artifact(job_id, "gaussian_scene.json")
    visibility = app.state.job_repository.read_artifact(job_id, "visibility_manifest.json")
    explorer_bundle = app.state.job_repository.read_artifact(job_id, "explorer_bundle.json")
    assert gaussian_scene["backend"] == "import"
    assert gaussian_scene["command_mode"] == "imported"
    assert len(visibility["cells"]) > 1
    assert explorer_bundle["viewer_render_mode"] == "splat"


def test_import_gaussian_route_rejects_incomplete_job(tmp_path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]

    response = client.post(
        f"/jobs/{job_id}/import-gaussian",
        files={"file": ("dense_scene.ply", _point_cloud_ply(3), "application/octet-stream")},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Job scene bundle is not ready for Gaussian import"


def test_imported_gaussian_scene_can_become_featured(tmp_path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    job_id = _completed_job(client, app)

    import_response = client.post(
        f"/jobs/{job_id}/import-gaussian",
        files={"file": ("featured_scene.ply", _point_cloud_ply(12001), "application/octet-stream")},
    )
    featured_response = client.get("/featured-job-scene-bundle")

    assert import_response.status_code == 200
    assert import_response.json()["featured_candidate"] is True
    assert featured_response.status_code == 200
    assert featured_response.json()["job_id"] == job_id


def _completed_job(client: TestClient, app) -> str:
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]
    _write_viewer_assets(app.state.job_repository, job_id)
    app.state.job_repository.complete_job(job_id, job_id)
    return job_id


def _point_cloud_ply(vertex_count: int) -> bytes:
    rows = "\n".join(
        f"{index * 0.01:.2f} 1.0 {-2.0 - (index * 0.01):.2f} 255 128 64"
        for index in range(vertex_count)
    )
    return (
        "ply\n"
        "format ascii 1.0\n"
        f"element vertex {vertex_count}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
        f"{rows}\n"
    ).encode("utf-8")


def _write_viewer_assets(job_repository, job_id: str) -> None:
    for artifact_name, payload in {
        "capture_quality.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "duration_sec": 4.2,
            "warnings": [],
        },
        "frame_extraction.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "backend": "ffmpeg",
            "command_mode": "external",
            "frame_count": 3,
        },
        "camera_motion.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "backend": "colmap",
            "command_mode": "external",
            "camera_path": "camera_path.json",
            "coordinate_system": "dreamnav_viewer_v1",
            "intrinsics_source": "colmap",
            "pose_count": 3,
        },
        "camera_path.json": {
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
                },
                {
                    "frame_index": 1,
                    "timestamp_sec": 0.5,
                    "position": [0.2, 1.55, -0.8],
                    "rotation_xyzw": [0, 0.02, 0, 0.9998],
                    "fov_degrees": 60,
                },
                {
                    "frame_index": 2,
                    "timestamp_sec": 1.0,
                    "position": [-0.2, 1.55, -1.0],
                    "rotation_xyzw": [0, -0.02, 0, 0.9998],
                    "fov_degrees": 60,
                },
            ],
        },
        "gaussian_scene.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "backend": "command",
            "command_mode": "external",
            "splat_file": "splat.ply",
            "gaussian_count": 24000,
            "splat_source": "existing",
            "splat_file_size_bytes": 32,
        },
        "metadata.json": {
            "scene_id": job_id,
            "title": "Processed walkthrough",
            "input_video": "walkthrough.mov",
            "duration_sec": 0,
            "frame_count": 3,
            "pose_backend": "colmap",
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
        },
        "quality.json": {
            "scene_id": job_id,
            "pose_backend": "colmap",
            "frame_count": 3,
            "visibility_threshold_observed": 3,
            "splat_fps": 0,
            "scene_model_training_sec": 184,
            "heldout_psnr_median": 21.4,
            "quality_gate": "warning",
            "completion_latency_ms_p50": None,
            "completion_latency_ms_p95": None,
            "runtime_path": "placeholder",
            "cached_completion": False,
        },
        "visibility_manifest.json": {
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
        },
        "completion_manifest.json": {
            "scene_id": job_id,
            "model_enabled": True,
            "architecture": "pose_conditioned_encoder_decoder",
            "quality_gate": "warning",
            "heldout_psnr_median": 21.4,
            "cache_strategy": "none",
            "cached_predictions": [],
        },
        "visibility_support.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "observed_threshold": 3,
            "method": "voxel_visibility_v1",
        },
        "training_views.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "train_views": 520,
            "heldout_views": 80,
        },
        "scene_model.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "architecture": "pose_conditioned_encoder_decoder",
            "training_time_sec": 184,
        },
        "heldout_evaluation.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "heldout_psnr_median": 21.4,
        },
        "quality_gate.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "heldout_psnr_median": 21.4,
            "quality_gate": "warning",
            "completion_policy": "warning_overlay",
            "quality_gate_reason": "Held-out PSNR is below 22 dB but at least 20 dB.",
            "warning_threshold_psnr": 20,
            "pass_threshold_psnr": 22,
        },
        "observed_zone.json": {
            "scene_id": job_id,
            "zone": "observed",
            "source_manifest": "visibility_manifest.json",
            "cell_count": 1,
            "coverage_ratio": 1.0,
            "bounds": {"min": [0, 1, -0.5], "max": [0, 1, -0.5]},
            "cells": ["cell_observed_001"],
        },
        "partial_zone.json": {
            "scene_id": job_id,
            "zone": "partial",
            "source_manifest": "visibility_manifest.json",
            "cell_count": 0,
            "coverage_ratio": 0.0,
            "bounds": None,
            "cells": [],
        },
        "completion_zone.json": {
            "scene_id": job_id,
            "zone": "completion",
            "source_manifest": "visibility_manifest.json",
            "cell_count": 0,
            "coverage_ratio": 0.0,
            "bounds": None,
            "cells": [],
        },
        "unknown_zone.json": {
            "scene_id": job_id,
            "zone": "unknown",
            "source_manifest": "visibility_manifest.json",
            "cell_count": 0,
            "coverage_ratio": 0.0,
            "bounds": None,
            "cells": [],
        },
    }.items():
        job_repository.write_artifact(job_id, artifact_name, payload)

    splat_path = job_repository.artifact_root(job_id) / "splat.ply"
    splat_path.parent.mkdir(parents=True, exist_ok=True)
    splat_path.write_bytes(b"ply\nformat ascii 1.0\nend_header\n")
