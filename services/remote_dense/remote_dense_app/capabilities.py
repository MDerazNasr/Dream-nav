from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .backend import detect_colmap_dense_support

if TYPE_CHECKING:
    from .main import RemoteDenseSettings


def remote_dense_capabilities(settings: RemoteDenseSettings) -> dict[str, object]:
    bundled_adapter = Path(settings.dense_command).is_file() if settings.dense_command else False
    colmap_supported, colmap_reason = detect_colmap_dense_support(settings.colmap_command)
    command_backend_ready = bundled_adapter

    missing_requirements: list[str] = []
    warnings: list[str] = []
    if settings.backend == "command" and not command_backend_ready:
        missing_requirements.append("Set DREAMNAV_REMOTE_DENSE_COMMAND to a valid executable.")
    if settings.backend in {"auto", "colmap_dense"} and not colmap_supported:
        warnings.append(colmap_reason or "COLMAP dense support is unavailable.")

    real_dense_ready = command_backend_ready or colmap_supported
    if not real_dense_ready:
        missing_requirements.append("Run the worker on a machine that can execute a real dense reconstruction backend.")

    return {
        "backend": settings.backend,
        "dense_command": settings.dense_command,
        "bundled_adapter_available": bundled_adapter,
        "colmap_command": settings.colmap_command,
        "colmap_dense_supported": colmap_supported,
        "colmap_dense_reason": colmap_reason,
        "allow_mock_fallback": settings.allow_mock_fallback,
        "retained_job_count": settings.retained_job_count,
        "real_dense_ready": real_dense_ready,
        "missing_requirements": missing_requirements,
        "warnings": warnings,
    }
