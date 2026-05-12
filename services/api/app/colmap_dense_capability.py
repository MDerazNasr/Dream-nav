from __future__ import annotations

from pathlib import Path
from shutil import which
from subprocess import run


def detect_colmap_dense_stereo_support(colmap_command: str | None) -> tuple[bool, str | None]:
    resolved_command = _resolve_command(colmap_command)
    if not resolved_command:
        return False, "Dense stereo support could not be checked because COLMAP is not available."

    completed = run(
        [resolved_command, "patch_match_stereo", "-h"],
        capture_output=True,
        check=False,
        text=True,
    )
    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    if "without CUDA" in output:
        return False, "The installed COLMAP build does not support dense stereo on this machine."

    if completed.returncode != 0:
        return False, "Dense stereo support could not be verified from the installed COLMAP build."

    return True, None


def _resolve_command(configured_command: str | None) -> str | None:
    if not configured_command:
        return which("colmap")

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)
