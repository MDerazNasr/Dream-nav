#!/usr/bin/env python3

from __future__ import annotations

from os import environ
from pathlib import Path
from shutil import which
from subprocess import run
from sys import argv, exit


class RemoteDenseDockerAdapterError(Exception):
    pass


def run_adapter(
    bundle_root: Path,
    artifacts_root: Path,
    frames_root: Path,
    output_ply: Path,
    docker_image: str | None = None,
    docker_runtime: str | None = None,
) -> None:
    try:
        bundle_root = bundle_root.resolve(strict=True)
        artifacts_root = artifacts_root.resolve(strict=True)
        frames_root = frames_root.resolve(strict=True)
    except FileNotFoundError as error:
        raise RemoteDenseDockerAdapterError("Remote dense bundle inputs were not found.") from error

    resolved_runtime = _resolve_runtime(docker_runtime)
    resolved_image = _resolve_image(docker_image)
    output_ply = output_ply.resolve()
    output_ply.parent.mkdir(parents=True, exist_ok=True)

    command = [
        resolved_runtime,
        "run",
        "--rm",
        "--mount",
        f"type=bind,src={bundle_root},dst=/dreamnav/bundle,ro",
        "--mount",
        f"type=bind,src={artifacts_root},dst=/dreamnav/artifacts,ro",
        "--mount",
        f"type=bind,src={frames_root},dst=/dreamnav/frames,ro",
        "--mount",
        f"type=bind,src={output_ply.parent},dst=/dreamnav/output",
        resolved_image,
        "--bundle-root",
        "/dreamnav/bundle",
        "--artifacts-root",
        "/dreamnav/artifacts",
        "--frames-root",
        "/dreamnav/frames",
        "--output-ply",
        f"/dreamnav/output/{output_ply.name}",
    ]
    completed = run(command, capture_output=True, check=False, text=True)
    if completed.returncode != 0 or not output_ply.is_file():
        details = completed.stderr.strip() or completed.stdout.strip() or "Docker dense adapter failed."
        raise RemoteDenseDockerAdapterError(details)

    print(f"remote_dense_docker_adapter image={resolved_image}")


def main(args: list[str]) -> int:
    try:
        parsed = _parse_args(args)
        run_adapter(
            bundle_root=Path(parsed["bundle_root"]),
            artifacts_root=Path(parsed["artifacts_root"]),
            frames_root=Path(parsed["frames_root"]),
            output_ply=Path(parsed["output_ply"]),
            docker_image=parsed.get("docker_image"),
            docker_runtime=parsed.get("docker_runtime"),
        )
    except RemoteDenseDockerAdapterError as error:
        print(str(error))
        return 1

    return 0


def _parse_args(args: list[str]) -> dict[str, str]:
    if len(args) not in {8, 10, 12}:
        raise SystemExit(
            "Usage: docker_command_adapter.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --output-ply <path> [--docker-image <image>] [--docker-runtime <cmd>]"
        )

    parsed = dict(zip(args[::2], args[1::2], strict=True))
    required = {"--bundle-root", "--artifacts-root", "--frames-root", "--output-ply"}
    allowed = required | {"--docker-image", "--docker-runtime"}
    if not required.issubset(parsed) or not set(parsed).issubset(allowed):
        raise SystemExit(
            "Usage: docker_command_adapter.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --output-ply <path> [--docker-image <image>] [--docker-runtime <cmd>]"
        )

    return {
        "bundle_root": parsed["--bundle-root"],
        "artifacts_root": parsed["--artifacts-root"],
        "frames_root": parsed["--frames-root"],
        "output_ply": parsed["--output-ply"],
        **({"docker_image": parsed["--docker-image"]} if "--docker-image" in parsed else {}),
        **({"docker_runtime": parsed["--docker-runtime"]} if "--docker-runtime" in parsed else {}),
    }


def _resolve_image(configured_image: str | None) -> str:
    image = configured_image or environ.get("DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE")
    if image:
        return image

    raise RemoteDenseDockerAdapterError(
        "Set DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE to a container image that implements the DreamNav dense command contract."
    )


def _resolve_runtime(configured_runtime: str | None) -> str:
    runtime = configured_runtime or environ.get("DREAMNAV_REMOTE_DENSE_DOCKER_RUNTIME") or "docker"
    resolved = which(runtime)
    if resolved:
        return resolved

    raise RemoteDenseDockerAdapterError(
        "Install Docker or set DREAMNAV_REMOTE_DENSE_DOCKER_RUNTIME to a compatible container runtime."
    )


if __name__ == "__main__":
    exit(main(argv[1:]))
