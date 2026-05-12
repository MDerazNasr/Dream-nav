from pathlib import Path

from fastapi.testclient import TestClient

from app.config import ApiSettings, ProcessingSettings
from app.main import create_app


def test_reconstruction_capabilities_reports_current_pipeline(tmp_path: Path) -> None:
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("#!/bin/sh\n", encoding="utf-8")
    ffmpeg.chmod(0o755)
    colmap = tmp_path / "colmap"
    colmap.write_text("#!/bin/sh\n", encoding="utf-8")
    colmap.chmod(0o755)
    gaussian_wrapper = tmp_path / "colmap_sparse_to_splat.py"
    gaussian_wrapper.write_text("#!/usr/bin/env python3\nprint('wrapper')\n", encoding="utf-8")
    gaussian_wrapper.chmod(0o755)
    client = TestClient(
        create_app(
            ApiSettings(
                repo_root=tmp_path,
                processing=ProcessingSettings(
                    frame_backend="ffmpeg",
                    frame_command=str(ffmpeg),
                    pose_backend="colmap",
                    pose_command=str(colmap),
                    gaussian_backend="command",
                    gaussian_command=str(gaussian_wrapper),
                ),
            )
        )
    )

    response = client.get("/reconstruction-capabilities")

    assert response.status_code == 200
    assert response.json()["pipeline_status"] == "real"
    assert response.json()["real_reconstruction_ready"] is True


def test_featured_job_scene_bundle_returns_latest_completed_scene(tmp_path: Path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]
    _write_viewer_assets(app.state.job_repository, job_id)
    app.state.job_repository.complete_job(job_id, job_id)

    response = client.get("/featured-job-scene-bundle")

    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    assert response.json()["output_scene_id"] == job_id


def test_featured_job_scene_bundle_returns_404_without_completed_scene(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))

    response = client.get("/featured-job-scene-bundle")

    assert response.status_code == 404
    assert response.json()["detail"] == "Featured job scene is not available"


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
        "camera_motion.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "backend": "colmap",
            "command_mode": "external",
            "camera_path": "camera_path.json",
            "coordinate_system": "dreamnav_viewer_v1",
            "intrinsics_source": "colmap",
            "pose_count": 1,
        },
        "camera_path.json": camera_path,
        "gaussian_scene.json": {
            "job_id": job_id,
            "source_video": "walkthrough.mov",
            "backend": "command",
            "command_mode": "external",
            "splat_file": "splat.ply",
            "gaussian_count": 12,
            "splat_source": "existing",
            "splat_file_size_bytes": 32,
        },
        "metadata.json": metadata,
        "quality.json": quality,
        "visibility_manifest.json": visibility,
        "completion_manifest.json": completion,
    }.items():
        job_repository.write_artifact(job_id, artifact_name, payload)

    splat_path = job_repository.artifact_root(job_id) / "splat.ply"
    splat_path.parent.mkdir(parents=True, exist_ok=True)
    splat_path.write_bytes(b"ply\nformat ascii 1.0\nend_header\n")
