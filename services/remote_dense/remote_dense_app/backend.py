from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import which
from subprocess import run
from sys import executable

from .generator import RemoteDenseGenerationError, extract_bundle, generate_mock_dense_ply_from_extracted


class RemoteDenseBackendError(Exception):
    pass


@dataclass(frozen=True)
class DenseBuildResult:
    backend: str
    dense_ply: bytes
    warnings: list[str]


def build_dense_result(
    bundle_path: Path,
    workspace_root: Path,
    backend: str,
    colmap_command: str | None,
    allow_mock_fallback: bool,
) -> DenseBuildResult:
    workspace_root.mkdir(parents=True, exist_ok=True)
    extracted_root = workspace_root / "bundle"
    extract_bundle(bundle_path, extracted_root)
    warnings: list[str] = []
    normalized_backend = backend.strip().lower()

    if normalized_backend == "mock":
        return DenseBuildResult("mock", generate_mock_dense_ply_from_extracted(extracted_root), warnings)

    if normalized_backend not in {"auto", "colmap_dense"}:
        raise RemoteDenseBackendError(f"Unsupported remote dense backend: {backend}")

    if not _bundle_has_colmap_sparse_model(extracted_root):
        if normalized_backend == "colmap_dense" or not allow_mock_fallback:
            raise RemoteDenseBackendError("Remote dense bundle did not include COLMAP sparse artifacts.")
        warnings.append("Falling back to mock dense output because the bundle did not include COLMAP sparse artifacts.")
        return DenseBuildResult("mock", generate_mock_dense_ply_from_extracted(extracted_root), warnings)

    supported, reason = detect_colmap_dense_support(colmap_command)
    if not supported:
        if normalized_backend == "colmap_dense" or not allow_mock_fallback:
            raise RemoteDenseBackendError(reason or "COLMAP dense backend is unavailable.")
        warnings.append(reason or "Falling back to mock dense output because COLMAP dense support is unavailable.")
        return DenseBuildResult("mock", generate_mock_dense_ply_from_extracted(extracted_root), warnings)

    try:
        dense_ply = build_dense_colmap_ply(extracted_root, workspace_root, colmap_command)
        return DenseBuildResult("colmap_dense", dense_ply, warnings)
    except RemoteDenseBackendError as error:
        if normalized_backend == "colmap_dense" or not allow_mock_fallback:
            raise
        warnings.append(f"Falling back to mock dense output because real dense reconstruction failed: {error}")
        return DenseBuildResult("mock", generate_mock_dense_ply_from_extracted(extracted_root), warnings)


def detect_colmap_dense_support(colmap_command: str | None) -> tuple[bool, str | None]:
    resolved_command = _resolve_colmap_command(colmap_command)
    if not resolved_command:
        return False, "COLMAP is not available for remote dense reconstruction."

    completed = run(
        [resolved_command, "patch_match_stereo", "-h"],
        capture_output=True,
        check=False,
        text=True,
    )
    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    if "without CUDA" in output:
        return False, "The configured COLMAP build does not support dense stereo."

    if completed.returncode != 0:
        return False, "COLMAP dense stereo support could not be verified."

    return True, None


def build_dense_colmap_ply(extracted_root: Path, workspace_root: Path, colmap_command: str | None) -> bytes:
    script_path = Path(__file__).resolve().parents[3] / "services" / "api" / "app" / "colmap_dense_to_splat.py"
    if not script_path.is_file():
        raise RemoteDenseBackendError("DreamNav COLMAP dense wrapper was not found.")

    output_splat = workspace_root / "dense_result.ply"
    command = [
        executable,
        str(script_path),
        "--artifacts-root",
        str(extracted_root / "artifacts"),
        "--frames-root",
        str(extracted_root / "frames"),
        "--camera-path",
        str(extracted_root / "artifacts" / "camera_path.json"),
        "--output-splat",
        str(output_splat),
    ]
    if colmap_command:
        command.extend(["--colmap-command", colmap_command])

    completed = run(
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0 or not output_splat.is_file():
        details = completed.stderr.strip() or completed.stdout.strip() or "Remote dense reconstruction failed."
        raise RemoteDenseBackendError(details)

    return output_splat.read_bytes()


def _bundle_has_colmap_sparse_model(extracted_root: Path) -> bool:
    return (extracted_root / "artifacts" / "colmap" / "sparse").is_dir()


def _resolve_colmap_command(configured_command: str | None) -> str | None:
    if not configured_command:
        return which("colmap")

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)
