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
