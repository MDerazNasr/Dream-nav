from __future__ import annotations

from os import environ
from pathlib import Path
from typing import TYPE_CHECKING

from .backend import detect_colmap_dense_support
from .docker_command_adapter import probe_engine as probe_docker_engine
from .gaussian_command_adapter import probe_engine as probe_gaussian_engine

if TYPE_CHECKING:
    from .main import RemoteDenseSettings


def remote_dense_capabilities(settings: RemoteDenseSettings) -> dict[str, object]:
    gaussian_adapter_path = Path(__file__).with_name("gaussian_command_adapter.py").resolve()
    bundled_adapter_path = Path(__file__).with_name("colmap_command_adapter.py").resolve()
    docker_adapter_path = Path(__file__).with_name("docker_command_adapter.py").resolve()
    gaussian_command_path = Path(settings.gaussian_command).resolve() if settings.gaussian_command else None
    dense_command_path = Path(settings.dense_command).resolve() if settings.dense_command else None
    gaussian_backend_configured = settings.gaussian_command is not None
    uses_gaussian_adapter = gaussian_command_path == gaussian_adapter_path if gaussian_command_path else False
    if uses_gaussian_adapter:
        gaussian_backend_ready, gaussian_reason = probe_gaussian_engine(
            environ.get("DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE")
        )
    else:
        gaussian_backend_ready = gaussian_command_path is not None and gaussian_command_path.is_file()
        gaussian_reason = None
    bundled_adapter = dense_command_path is not None and dense_command_path.is_file()
    uses_bundled_adapter = dense_command_path == bundled_adapter_path if dense_command_path else False
    uses_docker_adapter = dense_command_path == docker_adapter_path if dense_command_path else False
    colmap_supported, colmap_reason = detect_colmap_dense_support(settings.colmap_command)
    docker_image = environ.get("DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE")
    if uses_docker_adapter:
        docker_ready, docker_reason = _probe_docker_backend() if docker_image else (False, None)
        command_backend_ready = bundled_adapter and docker_ready
    else:
        command_backend_ready = bundled_adapter and (colmap_supported if uses_bundled_adapter else True)

    missing_requirements: list[str] = []
    warnings: list[str] = []
    if settings.backend == "gaussian_command" and not gaussian_backend_ready:
        missing_requirements.append("Set DREAMNAV_REMOTE_GAUSSIAN_COMMAND to a valid trained Gaussian backend executable.")
    if uses_gaussian_adapter and gaussian_reason:
        missing_requirements.append(gaussian_reason)
    if settings.backend == "command" and not command_backend_ready and not uses_docker_adapter:
        missing_requirements.append("Set DREAMNAV_REMOTE_DENSE_COMMAND to a valid executable.")
    if uses_docker_adapter and not docker_image:
        missing_requirements.append(
            "Set DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE to a container image that implements the DreamNav dense command contract."
        )
    if uses_docker_adapter and docker_image and docker_reason:
        missing_requirements.append(docker_reason)
    if settings.backend in {"auto", "colmap_dense"} and not colmap_supported:
        warnings.append(colmap_reason or "COLMAP dense support is unavailable.")

    real_dense_ready = gaussian_backend_ready or command_backend_ready or colmap_supported
    if not real_dense_ready:
        missing_requirements.append("Run the worker on a machine that can execute a real dense reconstruction backend.")

    return {
        "backend": settings.backend,
        "gaussian_command": settings.gaussian_command,
        "gaussian_backend_configured": gaussian_backend_configured,
        "gaussian_backend_ready": gaussian_backend_ready,
        "gaussian_backend_reason": gaussian_reason,
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


def _probe_docker_backend() -> tuple[bool, str | None]:
    try:
        return probe_docker_engine(
            docker_image=environ.get("DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE"),
            docker_runtime=environ.get("DREAMNAV_REMOTE_DENSE_DOCKER_RUNTIME"),
        )
    except Exception as error:
        return False, str(error)
