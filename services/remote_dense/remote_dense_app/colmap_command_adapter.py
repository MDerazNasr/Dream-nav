#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from shutil import which
from subprocess import run
from sys import argv, exit

try:
    from app.colmap_dense_to_splat import ColmapDenseToSplatError, build_dense_splat_from_colmap
except ImportError:
    candidate_roots = [
        Path(__file__).resolve().parents[3] / "services" / "api" / "app",
        Path(__file__).resolve().parents[1] / "app",
    ]
    for app_root in candidate_roots:
        if app_root.is_dir():
            if str(app_root) not in __import__("sys").path:
                __import__("sys").path.insert(0, str(app_root))
            from colmap_dense_to_splat import ColmapDenseToSplatError, build_dense_splat_from_colmap

            break
    else:
        raise


class RemoteDenseCommandAdapterError(Exception):
    pass


def run_adapter(
    bundle_root: Path,
    artifacts_root: Path,
    frames_root: Path,
    output_ply: Path,
    colmap_command: str | None = None,
) -> int:
    try:
        bundle_root.resolve(strict=True)
    except FileNotFoundError as error:
        raise RemoteDenseCommandAdapterError("Remote dense bundle root was not found.") from error

    try:
        vertex_count = build_dense_splat_from_colmap(
            artifacts_root=artifacts_root,
            frames_root=frames_root,
            output_splat=output_ply,
            colmap_command=colmap_command,
        )
    except ColmapDenseToSplatError as error:
        raise RemoteDenseCommandAdapterError(str(error)) from error

    print(f"remote_dense_command_adapter vertices={vertex_count}")
    return vertex_count


def run_health_check(colmap_command: str | None = None) -> int:
    resolved_command = _resolve_colmap_command(colmap_command)
    if not resolved_command:
        raise RemoteDenseCommandAdapterError("COLMAP is not available inside the dense engine image.")

    completed = run(
        [resolved_command, "patch_match_stereo", "-h"],
        capture_output=True,
        check=False,
        text=True,
    )
    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    if "without CUDA" in output or "requires CUDA" in output:
        raise RemoteDenseCommandAdapterError("The dense engine image COLMAP build does not support dense stereo.")
    if completed.returncode != 0:
        raise RemoteDenseCommandAdapterError("The dense engine image COLMAP dense stereo support could not be verified.")

    print("remote_dense_command_adapter health=ok")
    return 0


def main(args: list[str]) -> int:
    try:
        if args == ["--health-check"]:
            run_health_check()
            return 0
        parsed = _parse_args(args)
        run_adapter(
            bundle_root=Path(parsed["bundle_root"]),
            artifacts_root=Path(parsed["artifacts_root"]),
            frames_root=Path(parsed["frames_root"]),
            output_ply=Path(parsed["output_ply"]),
            colmap_command=parsed.get("colmap_command"),
        )
    except RemoteDenseCommandAdapterError as error:
        print(str(error))
        return 1

    return 0


def _parse_args(args: list[str]) -> dict[str, str]:
    if len(args) not in {8, 10}:
        raise SystemExit(
            "Usage: colmap_command_adapter.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --output-ply <path> [--colmap-command <cmd>]"
        )

    parsed = dict(zip(args[::2], args[1::2], strict=True))
    required = {"--bundle-root", "--artifacts-root", "--frames-root", "--output-ply"}
    allowed = required | {"--colmap-command"}
    if not required.issubset(parsed) or not set(parsed).issubset(allowed):
        raise SystemExit(
            "Usage: colmap_command_adapter.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --output-ply <path> [--colmap-command <cmd>]"
        )

    return {
        "bundle_root": parsed["--bundle-root"],
        "artifacts_root": parsed["--artifacts-root"],
        "frames_root": parsed["--frames-root"],
        "output_ply": parsed["--output-ply"],
        **({"colmap_command": parsed["--colmap-command"]} if "--colmap-command" in parsed else {}),
    }


def _resolve_colmap_command(configured_command: str | None) -> str | None:
    if not configured_command:
        return which("colmap")

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)


if __name__ == "__main__":
    exit(main(argv[1:]))
