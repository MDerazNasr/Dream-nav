#!/usr/bin/env python3

from __future__ import annotations

from json import JSONDecodeError, loads
from pathlib import Path
from shutil import which
from subprocess import CompletedProcess, run
from sys import argv, exit

try:
    from .point_cloud_to_splat import PointCloudToSplatError, read_ply_points, write_splat_from_points
except ImportError:
    from point_cloud_to_splat import PointCloudToSplatError, read_ply_points, write_splat_from_points

MAX_DENSE_POINTS = 40000


class ColmapDenseToSplatError(Exception):
    pass


def build_dense_splat_from_colmap(
    artifacts_root: Path,
    frames_root: Path,
    output_splat: Path,
    colmap_command: str | None = None,
    max_points: int = MAX_DENSE_POINTS,
) -> int:
    artifacts_root = artifacts_root.resolve()
    frames_root = frames_root.resolve()
    output_splat = output_splat.resolve()
    resolved_colmap = _resolve_colmap_command(colmap_command)
    sparse_model_root = _selected_sparse_model_root(artifacts_root)
    dense_root = artifacts_root / "colmap" / "dense"
    dense_root.mkdir(parents=True, exist_ok=True)

    _run_colmap(
        [
            resolved_colmap,
            "image_undistorter",
            "--image_path",
            str(frames_root),
            "--input_path",
            str(sparse_model_root),
            "--output_path",
            str(dense_root),
            "--output_type",
            "COLMAP",
        ],
        artifacts_root,
    )
    _run_colmap(
        [
            resolved_colmap,
            "patch_match_stereo",
            "--workspace_path",
            str(dense_root),
            "--workspace_format",
            "COLMAP",
            "--PatchMatchStereo.geom_consistency",
            "true",
        ],
        artifacts_root,
    )

    fused_path = dense_root / "fused.ply"
    _run_colmap(
        [
            resolved_colmap,
            "stereo_fusion",
            "--workspace_path",
            str(dense_root),
            "--workspace_format",
            "COLMAP",
            "--input_type",
            "geometric",
            "--output_path",
            str(fused_path),
        ],
        artifacts_root,
    )

    try:
        points = read_ply_points(fused_path)
        return write_splat_from_points(points, output_splat, max_points=max_points)
    except PointCloudToSplatError as error:
        raise ColmapDenseToSplatError(str(error)) from error


def _resolve_colmap_command(configured_command: str | None) -> str:
    if configured_command:
        configured_path = Path(configured_command)
        if configured_path.parent != Path("."):
            if configured_path.is_file():
                return str(configured_path)
        else:
            resolved = which(configured_command)
            if resolved:
                return resolved

    resolved_default = which("colmap")
    if resolved_default:
        return resolved_default

    raise ColmapDenseToSplatError("COLMAP is required for dense reconstruction but was not found.")


def _selected_sparse_model_root(artifacts_root: Path) -> Path:
    selection_path = artifacts_root / "colmap" / "colmap_model_selection.json"
    sparse_root = artifacts_root / "colmap" / "sparse"
    if not sparse_root.is_dir():
        raise ColmapDenseToSplatError("COLMAP sparse model directory is missing.")

    selected_model = _selected_model_name(selection_path)
    if selected_model is not None:
        candidate = sparse_root / selected_model
        if candidate.is_dir():
            return candidate

    model_roots = sorted(path for path in sparse_root.iterdir() if path.is_dir())
    if not model_roots:
        raise ColmapDenseToSplatError("COLMAP sparse model directory did not contain a model.")

    return model_roots[0]


def _selected_model_name(selection_path: Path) -> str | None:
    try:
        payload = loads(selection_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except JSONDecodeError as error:
        raise ColmapDenseToSplatError("COLMAP model selection artifact is invalid.") from error

    if not isinstance(payload, dict):
        raise ColmapDenseToSplatError("COLMAP model selection artifact is invalid.")

    selected_model = payload.get("selected_model")
    return selected_model if isinstance(selected_model, str) and selected_model else None


def _run_colmap(command: list[str], artifacts_root: Path) -> None:
    completed: CompletedProcess[str] = run(
        command,
        capture_output=True,
        check=False,
        cwd=str(artifacts_root),
        text=True,
    )
    print(" ".join(command))
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "COLMAP command failed."
        raise ColmapDenseToSplatError(details)


def main(args: list[str]) -> int:
    try:
        parsed = _parse_args(args)
        vertex_count = build_dense_splat_from_colmap(
            Path(parsed["artifacts_root"]),
            Path(parsed["frames_root"]),
            Path(parsed["output_splat"]),
            colmap_command=parsed.get("colmap_command"),
        )
    except ColmapDenseToSplatError as error:
        print(str(error))
        return 1

    print(f"generated_dense_splat vertices={vertex_count}")
    return 0


def _parse_args(args: list[str]) -> dict[str, str]:
    if len(args) not in {8, 10}:
        raise SystemExit(
            "Usage: colmap_dense_to_splat.py --artifacts-root <path> --frames-root <path> --camera-path <path> --output-splat <path> [--colmap-command <cmd>]"
        )

    parsed = dict(zip(args[::2], args[1::2], strict=True))
    required = {"--artifacts-root", "--frames-root", "--camera-path", "--output-splat"}
    allowed = required | {"--colmap-command"}
    if not required.issubset(parsed) or not set(parsed).issubset(allowed):
        raise SystemExit(
            "Usage: colmap_dense_to_splat.py --artifacts-root <path> --frames-root <path> --camera-path <path> --output-splat <path> [--colmap-command <cmd>]"
        )

    return {
        "artifacts_root": parsed["--artifacts-root"],
        "frames_root": parsed["--frames-root"],
        "output_splat": parsed["--output-splat"],
        **(
            {"colmap_command": parsed["--colmap-command"]}
            if "--colmap-command" in parsed
            else {}
        ),
    }


if __name__ == "__main__":
    exit(main(argv[1:]))
