from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError, loads
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, TimeoutExpired, run

from .jobs import SUPPORTED_VIDEO_EXTENSIONS

FFPROBE_TIMEOUT_SEC = 5


class VideoProbeError(Exception):
    pass


@dataclass(frozen=True)
class VideoProbeResult:
    file_size_bytes: int
    extension: str
    supported_extension: bool
    duration_sec: float | None
    probe_backend: str
    warnings: list[str]


def probe_video_file(video_path: Path) -> VideoProbeResult:
    if not video_path.is_file():
        raise VideoProbeError("Uploaded file is missing.")

    file_size_bytes = video_path.stat().st_size
    if file_size_bytes == 0:
        raise VideoProbeError("Uploaded file is empty.")

    extension = video_path.suffix.lower()
    warnings = []

    if extension not in SUPPORTED_VIDEO_EXTENSIONS:
        warnings.append("Use MP4, MOV, or M4V walkthrough videos for reconstruction.")

    duration_sec, probe_backend, probe_warning = _probe_duration(video_path)
    if probe_warning:
        warnings.append(probe_warning)

    return VideoProbeResult(
        file_size_bytes=file_size_bytes,
        extension=extension,
        supported_extension=extension in SUPPORTED_VIDEO_EXTENSIONS,
        duration_sec=duration_sec,
        probe_backend=probe_backend,
        warnings=warnings,
    )


def _probe_duration(video_path: Path) -> tuple[float | None, str, str | None]:
    ffprobe_path = which("ffprobe")
    if not ffprobe_path:
        return None, "filesystem", "Duration unavailable because ffprobe is not installed."

    try:
        completed = run(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=FFPROBE_TIMEOUT_SEC,
        )
        payload = loads(completed.stdout)
        duration = float(payload["format"]["duration"])
        return duration, "ffprobe", None
    except (CalledProcessError, JSONDecodeError, KeyError, TypeError, ValueError, TimeoutExpired):
        return None, "filesystem", "ffprobe could not read video duration."
