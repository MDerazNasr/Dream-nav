from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import which

from .config import ProcessingSettings


class GaussianReconstructionConfigError(Exception):
    pass


@dataclass(frozen=True)
class GaussianCommandSpec:
    artifact_name: str
    command: list[str]
    timeout_sec: float


def normalized_gaussian_backend(settings: ProcessingSettings) -> str:
    return settings.gaussian_backend.strip().lower()


def build_gaussian_reconstruction_command(
    settings: ProcessingSettings,
    artifacts_root: Path,
) -> GaussianCommandSpec:
    backend = normalized_gaussian_backend(settings)

    if backend == "stub":
        return GaussianCommandSpec(
            artifact_name="gaussian_scene_command.json",
            command=[
                _python_command(),
                "-c",
                f"print('gaussian_backend=stub artifacts={artifacts_root}')",
            ],
            timeout_sec=5,
        )

    if backend == "command":
        gaussian_command = _resolve_command(settings.gaussian_command)
        if not gaussian_command:
            raise GaussianReconstructionConfigError(
                "Gaussian backend command selected but DREAMNAV_GAUSSIAN_COMMAND was not found."
            )

        command = [
            gaussian_command,
            "--artifacts-root",
            str(artifacts_root),
            "--frames-root",
            str(artifacts_root / "frames"),
            "--camera-path",
            str(artifacts_root / "camera_path.json"),
            "--output-splat",
            str(artifacts_root / "splat.ply"),
        ]
        if settings.pose_command:
            command.extend(["--colmap-command", settings.pose_command])

        return GaussianCommandSpec(
            artifact_name="gaussian_scene_command.json",
            command=command,
            timeout_sec=settings.gaussian_timeout_sec,
        )

    raise GaussianReconstructionConfigError(f"Unsupported gaussian backend: {settings.gaussian_backend}")


def _resolve_command(configured_command: str | None) -> str | None:
    if not configured_command:
        return None

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)


def _python_command() -> str:
    import sys

    return sys.executable
