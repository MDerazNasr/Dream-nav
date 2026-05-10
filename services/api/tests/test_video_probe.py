from pathlib import Path

import pytest

from app.video_probe import VideoProbeError, probe_video_file


def test_probe_video_file_reports_filesystem_metadata(tmp_path: Path) -> None:
    video_path = tmp_path / "walkthrough.mp4"
    video_path.write_bytes(b"not-a-real-video")

    result = probe_video_file(video_path)

    assert result.file_size_bytes == len(b"not-a-real-video")
    assert result.extension == ".mp4"
    assert result.supported_extension is True
    assert result.duration_sec is None or result.duration_sec >= 0
    assert result.probe_backend in {"filesystem", "ffprobe"}


def test_probe_video_file_warns_for_unsupported_extension(tmp_path: Path) -> None:
    video_path = tmp_path / "walkthrough.txt"
    video_path.write_bytes(b"not-a-real-video")

    result = probe_video_file(video_path)

    assert result.supported_extension is False
    assert "Use MP4, MOV, or M4V walkthrough videos for reconstruction." in result.warnings


def test_probe_video_file_rejects_empty_file(tmp_path: Path) -> None:
    video_path = tmp_path / "walkthrough.mp4"
    video_path.write_bytes(b"")

    with pytest.raises(VideoProbeError, match="empty"):
        probe_video_file(video_path)


def test_probe_video_file_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(VideoProbeError, match="missing"):
        probe_video_file(tmp_path / "missing.mp4")
