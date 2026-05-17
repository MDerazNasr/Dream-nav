#!/usr/bin/env python3

from __future__ import annotations

from json import JSONDecodeError, loads
from os import environ
from pathlib import Path
from shutil import which
from subprocess import run
from sys import argv, exit


class TrainedGaussianBackendError(Exception):
    pass


def run_backend(
    bundle_root: Path,
    artifacts_root: Path,
    frames_root: Path,
    camera_path: Path,
    colmap_root: Path,
    output_ply: Path,
    train_command_json: str | None = None,
    export_command_json: str | None = None,
) -> None:
    try:
        bundle_root = bundle_root.resolve(strict=True)
        artifacts_root = artifacts_root.resolve(strict=True)
        frames_root = frames_root.resolve(strict=True)
        camera_path = camera_path.resolve(strict=True)
        colmap_root = colmap_root.resolve(strict=True)
    except FileNotFoundError as error:
        raise TrainedGaussianBackendError("Trained Gaussian backend inputs were not found.") from error

    output_ply = output_ply.resolve()
    output_ply.parent.mkdir(parents=True, exist_ok=True)
    workspace_root = output_ply.parent / "trained-gaussian-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    train_command = _configured_command(train_command_json, "DREAMNAV_TRAINED_GAUSSIAN_TRAIN_COMMAND_JSON")
    export_command = _configured_command(export_command_json, "DREAMNAV_TRAINED_GAUSSIAN_EXPORT_COMMAND_JSON", required=False)
    if train_command is None and export_command is None:
        raise TrainedGaussianBackendError(
            "Set DREAMNAV_TRAINED_GAUSSIAN_TRAIN_COMMAND_JSON to a command array for the trained Gaussian backend."
        )

    substitutions = {
        "bundle_root": str(bundle_root),
        "artifacts_root": str(artifacts_root),
        "frames_root": str(frames_root),
        "camera_path": str(camera_path),
        "colmap_root": str(colmap_root),
        "workspace_root": str(workspace_root),
        "output_ply": str(output_ply),
    }

    if train_command is not None:
        _run_command(_render_command(train_command, substitutions), workspace_root)
    if not output_ply.is_file() and export_command is not None:
        _run_command(_render_command(export_command, substitutions), workspace_root)

    if not output_ply.is_file():
        raise TrainedGaussianBackendError("Trained Gaussian backend did not produce the requested output PLY.")

    print(f"trained_gaussian_backend output={output_ply}")


def probe_backend(
    train_command_json: str | None = None,
    export_command_json: str | None = None,
) -> tuple[bool, str | None]:
    try:
        train_command = _configured_command(train_command_json, "DREAMNAV_TRAINED_GAUSSIAN_TRAIN_COMMAND_JSON", required=False)
        export_command = _configured_command(export_command_json, "DREAMNAV_TRAINED_GAUSSIAN_EXPORT_COMMAND_JSON", required=False)
    except TrainedGaussianBackendError as error:
        return False, str(error)

    command = train_command or export_command
    if command is None:
        return False, "Set DREAMNAV_TRAINED_GAUSSIAN_TRAIN_COMMAND_JSON to a command array for the trained Gaussian backend."

    executable = command[0]
    executable_path = Path(executable)
    if executable_path.parent != Path("."):
        if executable_path.is_file():
            return True, None
        return False, "Configured trained Gaussian command executable was not found."

    if which(executable):
        return True, None

    return False, "Configured trained Gaussian command executable was not found."


def main(args: list[str]) -> int:
    try:
        if args == ["--health-check"]:
            ready, reason = probe_backend()
            if not ready:
                raise TrainedGaussianBackendError(reason or "Trained Gaussian backend health check failed.")
            print("trained_gaussian_backend health=ok")
            return 0

        parsed = _parse_args(args)
        run_backend(
            bundle_root=Path(parsed["bundle_root"]),
            artifacts_root=Path(parsed["artifacts_root"]),
            frames_root=Path(parsed["frames_root"]),
            camera_path=Path(parsed["camera_path"]),
            colmap_root=Path(parsed["colmap_root"]),
            output_ply=Path(parsed["output_ply"]),
            train_command_json=parsed.get("train_command_json"),
            export_command_json=parsed.get("export_command_json"),
        )
    except TrainedGaussianBackendError as error:
        print(str(error))
        return 1

    return 0


def _parse_args(args: list[str]) -> dict[str, str]:
    if len(args) not in {12, 14, 16}:
        raise SystemExit(
            "Usage: trained_gaussian_backend.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --camera-path <path> --colmap-root <path> --output-ply <path> [--train-command-json <json>] [--export-command-json <json>]"
        )

    parsed = dict(zip(args[::2], args[1::2], strict=True))
    required = {"--bundle-root", "--artifacts-root", "--frames-root", "--camera-path", "--colmap-root", "--output-ply"}
    allowed = required | {"--train-command-json", "--export-command-json"}
    if not required.issubset(parsed) or not set(parsed).issubset(allowed):
        raise SystemExit(
            "Usage: trained_gaussian_backend.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --camera-path <path> --colmap-root <path> --output-ply <path> [--train-command-json <json>] [--export-command-json <json>]"
        )

    return {
        "bundle_root": parsed["--bundle-root"],
        "artifacts_root": parsed["--artifacts-root"],
        "frames_root": parsed["--frames-root"],
        "camera_path": parsed["--camera-path"],
        "colmap_root": parsed["--colmap-root"],
        "output_ply": parsed["--output-ply"],
        **({"train_command_json": parsed["--train-command-json"]} if "--train-command-json" in parsed else {}),
        **({"export_command_json": parsed["--export-command-json"]} if "--export-command-json" in parsed else {}),
    }


def _configured_command(
    explicit_json: str | None,
    env_name: str,
    required: bool = True,
) -> list[str] | None:
    payload = explicit_json if explicit_json is not None else environ.get(env_name)
    if payload is None:
        if required:
            raise TrainedGaussianBackendError(f"Set {env_name} to a JSON command array.")
        return None

    try:
        parsed = loads(payload)
    except JSONDecodeError as error:
        raise TrainedGaussianBackendError(f"{env_name} must be valid JSON.") from error

    if not isinstance(parsed, list) or not parsed or not all(isinstance(item, str) and item for item in parsed):
        raise TrainedGaussianBackendError(f"{env_name} must be a non-empty JSON array of strings.")

    return parsed


def _render_command(command: list[str], substitutions: dict[str, str]) -> list[str]:
    return [part.format(**substitutions) for part in command]


def _run_command(command: list[str], workspace_root: Path) -> None:
    completed = run(command, capture_output=True, check=False, text=True, cwd=str(workspace_root))
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "Trained Gaussian command failed."
        raise TrainedGaussianBackendError(details)


if __name__ == "__main__":
    exit(main(argv[1:]))
