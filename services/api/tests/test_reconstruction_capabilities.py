from pathlib import Path

from app.config import ProcessingSettings
from app.reconstruction_capabilities import detect_reconstruction_capabilities


def test_detect_reconstruction_capabilities_reports_stub_pipeline() -> None:
    capabilities = detect_reconstruction_capabilities(ProcessingSettings())

    assert capabilities.pipeline_status == "stub"
    assert capabilities.real_reconstruction_ready is False
    assert capabilities.dense_reconstruction_ready is False
    assert "Set DREAMNAV_FRAME_BACKEND=ffmpeg to extract real video frames." in capabilities.missing_requirements


def test_detect_reconstruction_capabilities_reports_mixed_pipeline() -> None:
    capabilities = detect_reconstruction_capabilities(
        ProcessingSettings(
            frame_backend="ffmpeg",
            frame_command="/opt/homebrew/bin/ffmpeg",
            pose_backend="stub",
            gaussian_backend="stub",
        )
    )

    assert capabilities.pipeline_status == "mixed"
    assert capabilities.frame_command == "/opt/homebrew/bin/ffmpeg"
    assert capabilities.pose_command is None
    assert capabilities.gaussian_command is None
    assert capabilities.dense_reconstruction_ready is False


def test_detect_reconstruction_capabilities_reports_real_pipeline(tmp_path: Path, monkeypatch) -> None:
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("#!/bin/sh\n", encoding="utf-8")
    ffmpeg.chmod(0o755)
    colmap = tmp_path / "colmap"
    colmap.write_text("#!/bin/sh\n", encoding="utf-8")
    colmap.chmod(0o755)
    gaussian_wrapper = tmp_path / "colmap_sparse_to_splat.py"
    gaussian_wrapper.write_text("#!/usr/bin/env python3\nprint('wrapper')\n", encoding="utf-8")
    gaussian_wrapper.chmod(0o755)
    monkeypatch.setattr(
        "app.reconstruction_capabilities.detect_colmap_dense_stereo_support",
        lambda _command: (True, None),
    )

    capabilities = detect_reconstruction_capabilities(
        ProcessingSettings(
            frame_backend="ffmpeg",
            frame_command=str(ffmpeg),
            pose_backend="colmap",
            pose_command=str(colmap),
            gaussian_backend="command",
            gaussian_command=str(gaussian_wrapper),
        )
    )

    assert capabilities.pipeline_status == "real"
    assert capabilities.real_reconstruction_ready is True
    assert capabilities.dense_reconstruction_ready is True
    assert capabilities.dense_reconstruction_reason is None
    assert capabilities.missing_requirements == []


def test_detect_reconstruction_capabilities_reports_real_but_not_dense_pipeline(tmp_path: Path, monkeypatch) -> None:
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("#!/bin/sh\n", encoding="utf-8")
    ffmpeg.chmod(0o755)
    colmap = tmp_path / "colmap"
    colmap.write_text("#!/bin/sh\n", encoding="utf-8")
    colmap.chmod(0o755)
    gaussian_wrapper = tmp_path / "colmap_sparse_to_splat.py"
    gaussian_wrapper.write_text("#!/usr/bin/env python3\nprint('wrapper')\n", encoding="utf-8")
    gaussian_wrapper.chmod(0o755)
    monkeypatch.setattr(
        "app.reconstruction_capabilities.detect_colmap_dense_stereo_support",
        lambda _command: (False, "The installed COLMAP build does not support dense stereo on this machine."),
    )

    capabilities = detect_reconstruction_capabilities(
        ProcessingSettings(
            frame_backend="ffmpeg",
            frame_command=str(ffmpeg),
            pose_backend="colmap",
            pose_command=str(colmap),
            gaussian_backend="command",
            gaussian_command=str(gaussian_wrapper),
        )
    )

    assert capabilities.pipeline_status == "real"
    assert capabilities.real_reconstruction_ready is True
    assert capabilities.dense_reconstruction_ready is False
    assert capabilities.dense_reconstruction_reason == "The installed COLMAP build does not support dense stereo on this machine."
    assert "The installed COLMAP build does not support dense stereo on this machine." in capabilities.warnings
