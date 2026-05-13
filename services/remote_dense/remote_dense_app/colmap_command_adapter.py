#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from sys import argv, exit

try:
    from app.colmap_dense_to_splat import ColmapDenseToSplatError, build_dense_splat_from_colmap
except ImportError:
    services_root = Path(__file__).resolve().parents[3] / "services" / "api"
    if str(services_root) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(services_root))
    from app.colmap_dense_to_splat import ColmapDenseToSplatError, build_dense_splat_from_colmap


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


def main(args: list[str]) -> int:
    try:
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


if __name__ == "__main__":
    exit(main(argv[1:]))
