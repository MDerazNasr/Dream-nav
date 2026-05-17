#!/usr/bin/env python3

from __future__ import annotations

from os import environ
from pathlib import Path
from shutil import which
from subprocess import run
from sys import argv, exit


class RemoteGaussianCommandAdapterError(Exception):
    pass


def run_adapter(
    bundle_root: Path,
    artifacts_root: Path,
    frames_root: Path,
    output_ply: Path,
    gaussian_executable: str | None = None,
) -> None:
    try:
        bundle_root = bundle_root.resolve(strict=True)
        artifacts_root = artifacts_root.resolve(strict=True)
        frames_root = frames_root.resolve(strict=True)
    except FileNotFoundError as error:
        raise RemoteGaussianCommandAdapterError("Remote Gaussian bundle inputs were not found.") from error

    resolved_executable = _resolve_gaussian_executable(gaussian_executable)
    output_ply = output_ply.resolve()
    output_ply.parent.mkdir(parents=True, exist_ok=True)

    command = [
        resolved_executable,
        "--bundle-root",
        str(bundle_root),
        "--artifacts-root",
        str(artifacts_root),
        "--frames-root",
        str(frames_root),
        "--camera-path",
        str(artifacts_root / "camera_path.json"),
        "--colmap-root",
        str(artifacts_root / "colmap"),
        "--output-ply",
        str(output_ply),
    ]
    completed = run(command, capture_output=True, check=False, text=True)
    if completed.returncode != 0 or not output_ply.is_file():
        details = completed.stderr.strip() or completed.stdout.strip() or "Trained Gaussian adapter failed."
        raise RemoteGaussianCommandAdapterError(details)

    print(f"remote_gaussian_command_adapter executable={resolved_executable}")


def probe_engine(gaussian_executable: str | None = None) -> tuple[bool, str | None]:
    try:
        resolved_executable = _resolve_gaussian_executable(gaussian_executable)
    except RemoteGaussianCommandAdapterError as error:
        return False, str(error)

    completed = run(
        [resolved_executable, "--health-check"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode == 0:
        return True, None

    fallback = run(
        [resolved_executable, "--help"],
        capture_output=True,
        check=False,
        text=True,
    )
    if fallback.returncode == 0:
        return True, None

    details = completed.stderr.strip() or completed.stdout.strip() or fallback.stderr.strip() or fallback.stdout.strip()
    return False, details or "Trained Gaussian backend health check failed."


def main(args: list[str]) -> int:
    try:
        if args == ["--health-check"]:
            ok, reason = probe_engine()
            if not ok:
                raise RemoteGaussianCommandAdapterError(reason or "Trained Gaussian backend health check failed.")
            print("remote_gaussian_command_adapter health=ok")
            return 0

        parsed = _parse_args(args)
        run_adapter(
            bundle_root=Path(parsed["bundle_root"]),
            artifacts_root=Path(parsed["artifacts_root"]),
            frames_root=Path(parsed["frames_root"]),
            output_ply=Path(parsed["output_ply"]),
            gaussian_executable=parsed.get("gaussian_executable"),
        )
    except RemoteGaussianCommandAdapterError as error:
        print(str(error))
        return 1

    return 0


def _parse_args(args: list[str]) -> dict[str, str]:
    if len(args) not in {8, 10}:
        raise SystemExit(
            "Usage: gaussian_command_adapter.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --output-ply <path> [--gaussian-executable <cmd>]"
        )

    parsed = dict(zip(args[::2], args[1::2], strict=True))
    required = {"--bundle-root", "--artifacts-root", "--frames-root", "--output-ply"}
    allowed = required | {"--gaussian-executable"}
    if not required.issubset(parsed) or not set(parsed).issubset(allowed):
        raise SystemExit(
            "Usage: gaussian_command_adapter.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --output-ply <path> [--gaussian-executable <cmd>]"
        )

    return {
        "bundle_root": parsed["--bundle-root"],
        "artifacts_root": parsed["--artifacts-root"],
        "frames_root": parsed["--frames-root"],
        "output_ply": parsed["--output-ply"],
        **({"gaussian_executable": parsed["--gaussian-executable"]} if "--gaussian-executable" in parsed else {}),
    }


def _resolve_gaussian_executable(configured_executable: str | None) -> str:
    executable = configured_executable or environ.get("DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE")
    if not executable:
        raise RemoteGaussianCommandAdapterError(
            "Set DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE to the trained Gaussian backend executable."
        )

    executable_path = Path(executable)
    if executable_path.parent != Path("."):
        if executable_path.is_file():
            return str(executable_path)
        raise RemoteGaussianCommandAdapterError("Configured trained Gaussian backend executable was not found.")

    resolved = which(executable)
    if resolved:
        return resolved

    raise RemoteGaussianCommandAdapterError("Configured trained Gaussian backend executable was not found.")


if __name__ == "__main__":
    exit(main(argv[1:]))
