from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import which
from subprocess import run
from sys import executable
from typing import Callable

from .generator import RemoteDenseGenerationError, extract_bundle, generate_mock_dense_ply_from_extracted

try:
    from app.point_cloud_to_splat import PointCloudToSplatError, read_ply_points, write_splat_from_points
except ImportError:
    api_root = Path(__file__).resolve().parents[3] / "services" / "api"
    if str(api_root) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(api_root))
    from app.point_cloud_to_splat import PointCloudToSplatError, read_ply_points, write_splat_from_points


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
    dense_command: str | None,
    allow_mock_fallback: bool,
) -> DenseBuildResult:
    workspace_root.mkdir(parents=True, exist_ok=True)
    extracted_root = workspace_root / "bundle"
    extract_bundle(bundle_path, extracted_root)
    warnings: list[str] = []
    normalized_backend = backend.strip().lower()

    if normalized_backend == "mock":
        return DenseBuildResult("mock", generate_mock_dense_ply_from_extracted(extracted_root), warnings)

    if normalized_backend not in {"auto", "colmap_dense", "command"}:
        raise RemoteDenseBackendError(f"Unsupported remote dense backend: {backend}")

    if normalized_backend == "command":
        return DenseBuildResult(
            "command",
            build_dense_command_ply(extracted_root, workspace_root, dense_command),
            warnings,
        )

    if normalized_backend == "auto":
        for candidate_backend, builder in _auto_builders(extracted_root, workspace_root, colmap_command, dense_command):
            try:
                return DenseBuildResult(candidate_backend, builder(), warnings)
            except RemoteDenseBackendError as error:
                warnings.append(f"{candidate_backend}: {error}")
        if not allow_mock_fallback:
            raise RemoteDenseBackendError("No configured dense backend could build a remote dense result.")
        return DenseBuildResult("mock", generate_mock_dense_ply_from_extracted(extracted_root), warnings)

    return DenseBuildResult(
        "colmap_dense",
        build_dense_colmap_ply(extracted_root, workspace_root, colmap_command),
        warnings,
    )


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
    if "without CUDA" in output or "requires CUDA" in output:
        return False, "The configured COLMAP build does not support dense stereo."

    if completed.returncode != 0:
        return False, "COLMAP dense stereo support could not be verified."

    return True, None


def build_dense_colmap_ply(extracted_root: Path, workspace_root: Path, colmap_command: str | None) -> bytes:
    if not _bundle_has_colmap_sparse_model(extracted_root):
        raise RemoteDenseBackendError("Remote dense bundle did not include COLMAP sparse artifacts.")

    supported, reason = detect_colmap_dense_support(colmap_command)
    if not supported:
        raise RemoteDenseBackendError(reason or "COLMAP dense backend is unavailable.")

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


def build_dense_command_ply(extracted_root: Path, workspace_root: Path, dense_command: str | None) -> bytes:
    resolved_command = _resolve_dense_command(dense_command)
    if not resolved_command:
        raise RemoteDenseBackendError("DREAMNAV_REMOTE_DENSE_COMMAND was not found.")

    output_ply = workspace_root / "command_dense_result.ply"
    command = [
        resolved_command,
        "--bundle-root",
        str(extracted_root),
        "--artifacts-root",
        str(extracted_root / "artifacts"),
        "--frames-root",
        str(extracted_root / "frames"),
        "--output-ply",
        str(output_ply),
    ]
    completed = run(
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0 or not output_ply.is_file():
        details = completed.stderr.strip() or completed.stdout.strip() or "Remote dense command backend failed."
        raise RemoteDenseBackendError(details)

    return _normalize_dense_output(output_ply)


def _auto_builders(
    extracted_root: Path,
    workspace_root: Path,
    colmap_command: str | None,
    dense_command: str | None,
) -> list[tuple[str, Callable[[], bytes]]]:
    builders: list[tuple[str, Callable[[], bytes]]] = []
    if dense_command:
        builders.append(("command", lambda: build_dense_command_ply(extracted_root, workspace_root, dense_command)))
    builders.append(("colmap_dense", lambda: build_dense_colmap_ply(extracted_root, workspace_root, colmap_command)))
    return builders


def _bundle_has_colmap_sparse_model(extracted_root: Path) -> bool:
    return (extracted_root / "artifacts" / "colmap" / "sparse").is_dir()


def _resolve_colmap_command(configured_command: str | None) -> str | None:
    if not configured_command:
        return which("colmap")

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)


def _resolve_dense_command(configured_command: str | None) -> str | None:
    if not configured_command:
        return None

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)


def _normalize_dense_output(output_ply: Path) -> bytes:
    header = _ply_header(output_ply)
    if _is_splat_ply_header(header):
        return output_ply.read_bytes()

    try:
        points = read_ply_points(output_ply)
        write_splat_from_points(points, output_ply, max_points=40000)
    except PointCloudToSplatError as error:
        raise RemoteDenseBackendError(f"Remote dense command output could not be normalized: {error}") from error

    return output_ply.read_bytes()


def _ply_header(output_ply: Path) -> str:
    payload = output_ply.read_bytes()
    marker = b"end_header"
    header_end = payload.find(marker)
    if header_end == -1:
        raise RemoteDenseBackendError("Remote dense command output was not a valid PLY file.")

    newline_index = payload.find(b"\n", header_end)
    if newline_index == -1:
        newline_index = header_end + len(marker)

    return payload[:newline_index].decode("utf-8", errors="replace")


def _is_splat_ply_header(header: str) -> bool:
    return all(
        token in header
        for token in (
            "property float f_dc_0",
            "property float opacity",
            "property float scale_0",
            "property float rot_0",
        )
    )
