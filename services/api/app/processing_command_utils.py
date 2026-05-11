from __future__ import annotations

from pathlib import Path
from shutil import which
import sys

from .processing_models import ProcessingCommand


def resolve_command(configured_command: str | None, default_command: str) -> str | None:
    if not configured_command:
        return which(default_command)

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)


def placeholder_command(artifact_name: str, message: str) -> ProcessingCommand:
    return ProcessingCommand(
        artifact_name=artifact_name,
        command=[sys.executable, "-c", f"print({message!r})"],
        timeout_sec=5,
    )
