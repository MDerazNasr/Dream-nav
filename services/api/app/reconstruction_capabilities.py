from __future__ import annotations

from pathlib import Path
from shutil import which

from .config import ProcessingSettings
from .schemas import ReconstructionCapabilities


def detect_reconstruction_capabilities(settings: ProcessingSettings) -> ReconstructionCapabilities:
    frame_backend = settings.frame_backend.strip().lower()
    pose_backend = settings.pose_backend.strip().lower()
    gaussian_backend = settings.gaussian_backend.strip().lower()

    frame_command = _resolve_command(settings.frame_command, "ffmpeg") if frame_backend == "ffmpeg" else None
    pose_command = _resolve_command(settings.pose_command, "colmap") if pose_backend == "colmap" else None
    gaussian_command = _resolve_command(settings.gaussian_command, None) if gaussian_backend == "command" else None

    missing_requirements = _missing_requirements(
        frame_backend,
        pose_backend,
        gaussian_backend,
        frame_command,
        pose_command,
        gaussian_command,
    )
    pipeline_status = _pipeline_status(frame_backend, pose_backend, gaussian_backend, missing_requirements)
    warnings = _warnings(frame_backend, pose_backend, gaussian_backend, pipeline_status)

    return ReconstructionCapabilities(
        frame_backend=frame_backend,
        pose_backend=pose_backend,
        gaussian_backend=gaussian_backend,
        frame_command=frame_command,
        pose_command=pose_command,
        gaussian_command=gaussian_command,
        pipeline_status=pipeline_status,
        real_reconstruction_ready=pipeline_status == "real",
        missing_requirements=missing_requirements,
        warnings=warnings,
    )


def _resolve_command(configured_command: str | None, default_command: str | None) -> str | None:
    if configured_command:
        configured_path = Path(configured_command)
        if configured_path.parent != Path("."):
            return str(configured_path) if configured_path.is_file() else None

        return which(configured_command)

    if not default_command:
        return None

    return which(default_command)


def _missing_requirements(
    frame_backend: str,
    pose_backend: str,
    gaussian_backend: str,
    frame_command: str | None,
    pose_command: str | None,
    gaussian_command: str | None,
) -> list[str]:
    missing = []

    if frame_backend == "stub":
        missing.append("Set DREAMNAV_FRAME_BACKEND=ffmpeg to extract real video frames.")
    elif frame_backend == "ffmpeg" and not frame_command:
        missing.append("Install ffmpeg or set DREAMNAV_FRAME_COMMAND to the ffmpeg binary.")

    if pose_backend == "stub":
        missing.append("Install COLMAP and set DREAMNAV_POSE_BACKEND=colmap.")
    elif pose_backend == "colmap" and not pose_command:
        missing.append("Install COLMAP or set DREAMNAV_POSE_COMMAND to the COLMAP binary.")

    if gaussian_backend == "stub":
        missing.append(
            "Set DREAMNAV_GAUSSIAN_BACKEND=command and DREAMNAV_GAUSSIAN_COMMAND to a real reconstruction wrapper."
        )
    elif gaussian_backend == "command" and not gaussian_command:
        missing.append("Set DREAMNAV_GAUSSIAN_COMMAND to an executable that writes splat.ply.")

    return missing


def _pipeline_status(
    frame_backend: str,
    pose_backend: str,
    gaussian_backend: str,
    missing_requirements: list[str],
) -> str:
    if frame_backend == pose_backend == gaussian_backend == "stub":
        return "stub"

    if not missing_requirements:
        return "real"

    return "mixed"


def _warnings(
    frame_backend: str,
    pose_backend: str,
    gaussian_backend: str,
    pipeline_status: str,
) -> list[str]:
    warnings = []

    if pipeline_status != "real":
        warnings.append("The current pipeline still falls back to placeholder geometry.")

    if "stub" in {frame_backend, pose_backend, gaussian_backend}:
        warnings.append("Uploads will not produce a measured 3D reconstruction until every backend leaves stub mode.")

    return warnings
