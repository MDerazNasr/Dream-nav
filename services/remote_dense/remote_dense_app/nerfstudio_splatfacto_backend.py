#!/usr/bin/env python3

from __future__ import annotations

from os import environ, symlink
from pathlib import Path
from shutil import copy2, which
from subprocess import run
from sys import argv, exit

from remote_dense_app.nerfstudio_backend_error import NerfstudioSplatfactoBackendError
from remote_dense_app.nerfstudio_dataset_writer import (
    colmap_applied_transform,
    write_sparse_point_cloud,
    write_transforms,
)


def run_backend(
    bundle_root: Path,
    artifacts_root: Path,
    frames_root: Path,
    camera_path: Path,
    colmap_root: Path,
    output_ply: Path,
    train_command: str | None = None,
    export_command: str | None = None,
) -> None:
    try:
        bundle_root = bundle_root.resolve(strict=True)
        artifacts_root = artifacts_root.resolve(strict=True)
        frames_root = frames_root.resolve(strict=True)
        camera_path = camera_path.resolve(strict=True)
        colmap_root = colmap_root.resolve(strict=True)
    except FileNotFoundError as error:
        raise NerfstudioSplatfactoBackendError("Nerfstudio backend inputs were not found.") from error

    workspace_root = output_ply.resolve().parent / "nerfstudio-splatfacto-workspace"
    dataset_root = workspace_root / "dataset"
    images_root = dataset_root / "images"
    colmap_dataset_root = dataset_root / "colmap" / "sparse" / "0"
    outputs_root = workspace_root / "outputs"
    export_root = workspace_root / "export"
    images_root.mkdir(parents=True, exist_ok=True)
    colmap_dataset_root.mkdir(parents=True, exist_ok=True)
    outputs_root.mkdir(parents=True, exist_ok=True)
    export_root.mkdir(parents=True, exist_ok=True)

    frame_names = _materialize_images(frames_root, images_root)
    using_official_colmap = _materialize_colmap_dataset(colmap_root, colmap_dataset_root)
    if not using_official_colmap:
        applied_transform = colmap_applied_transform()
        sparse_point_cloud = write_sparse_point_cloud(colmap_root, dataset_root / "sparse_pc.ply", applied_transform)
        write_transforms(
            camera_path,
            colmap_root,
            dataset_root / "transforms.json",
            frame_names,
            sparse_point_cloud,
            applied_transform,
        )

    resolved_train = _resolve_command(train_command or environ.get("DREAMNAV_NERFSTUDIO_TRAIN_COMMAND") or "ns-train")
    resolved_export = _resolve_command(export_command or environ.get("DREAMNAV_NERFSTUDIO_EXPORT_COMMAND") or "ns-export")
    if not resolved_train:
        raise NerfstudioSplatfactoBackendError("Nerfstudio train command was not found.")
    if not resolved_export:
        raise NerfstudioSplatfactoBackendError("Nerfstudio export command was not found.")

    train_args = [
        resolved_train,
        environ.get("DREAMNAV_NERFSTUDIO_METHOD", "splatfacto"),
        "--data",
        str(dataset_root),
        "--vis",
        environ.get("DREAMNAV_NERFSTUDIO_VIS", "tensorboard"),
    ]
    if using_official_colmap:
        # Use Nerfstudio's own COLMAP parser so DreamNav does not have to emulate its dataset conventions.
        train_args.extend(
            [
                "colmap",
                "--orientation-method",
                environ.get("DREAMNAV_NERFSTUDIO_ORIENTATION_METHOD", "none"),
                "--center-method",
                environ.get("DREAMNAV_NERFSTUDIO_CENTER_METHOD", "none"),
                "--auto-scale-poses",
                environ.get("DREAMNAV_NERFSTUDIO_AUTO_SCALE_POSES", "False"),
                "--assume-colmap-world-coordinate-convention",
                environ.get("DREAMNAV_NERFSTUDIO_ASSUME_COLMAP_WORLD_CONVENTION", "False"),
                "--eval-mode",
                environ.get("DREAMNAV_NERFSTUDIO_EVAL_MODE", "all"),
                "--downscale-factor",
                environ.get("DREAMNAV_NERFSTUDIO_DOWNSCALE_FACTOR", "1"),
                "--images-path",
                "images",
                "--colmap-path",
                "colmap/sparse/0",
            ]
        )
        # Indoor walkthroughs are not a bounded forward-facing capture, so the default collider
        # can clip away valid room structure and leave only blob-like fragments.
        if environ.get("DREAMNAV_NERFSTUDIO_ENABLE_COLLIDER", "False").lower() not in {"1", "true", "yes", "on"}:
            train_args.extend(
                [
                    "--pipeline.model.enable-collider",
                    "False",
                ]
            )
    if "viewer" in environ.get("DREAMNAV_NERFSTUDIO_VIS", "tensorboard"):
        train_args.extend(
            [
                "--viewer.quit-on-train-completion",
                environ.get("DREAMNAV_NERFSTUDIO_VIEWER_QUIT_ON_COMPLETION", "True"),
            ]
        )

    _run_command(
        train_args,
        workspace_root,
    )

    config_path = _find_config_path(outputs_root)
    _run_command(
        [
            resolved_export,
            "gaussian-splat",
            "--load-config",
            str(config_path),
            "--output-dir",
            str(export_root),
        ],
        workspace_root,
    )

    exported_ply = _find_exported_ply(export_root)
    copy2(exported_ply, output_ply)
    print(f"nerfstudio_splatfacto_backend output={output_ply}")


def probe_backend(train_command: str | None = None, export_command: str | None = None) -> tuple[bool, str | None]:
    resolved_train = _resolve_command(train_command or environ.get("DREAMNAV_NERFSTUDIO_TRAIN_COMMAND") or "ns-train")
    resolved_export = _resolve_command(export_command or environ.get("DREAMNAV_NERFSTUDIO_EXPORT_COMMAND") or "ns-export")
    if not resolved_train:
        return False, "Nerfstudio train command was not found."
    if not resolved_export:
        return False, "Nerfstudio export command was not found."
    return True, None


def main(args: list[str]) -> int:
    try:
        if args == ["--health-check"]:
            ready, reason = probe_backend()
            if not ready:
                raise NerfstudioSplatfactoBackendError(reason or "Nerfstudio backend health check failed.")
            print("nerfstudio_splatfacto_backend health=ok")
            return 0

        parsed = _parse_args(args)
        run_backend(
            bundle_root=Path(parsed["bundle_root"]),
            artifacts_root=Path(parsed["artifacts_root"]),
            frames_root=Path(parsed["frames_root"]),
            camera_path=Path(parsed["camera_path"]),
            colmap_root=Path(parsed["colmap_root"]),
            output_ply=Path(parsed["output_ply"]),
            train_command=parsed.get("train_command"),
            export_command=parsed.get("export_command"),
        )
    except NerfstudioSplatfactoBackendError as error:
        print(str(error))
        return 1

    return 0


def _parse_args(args: list[str]) -> dict[str, str]:
    if len(args) not in {12, 14, 16}:
        raise SystemExit(
            "Usage: nerfstudio_splatfacto_backend.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --camera-path <path> --colmap-root <path> --output-ply <path> [--train-command <cmd>] [--export-command <cmd>]"
        )

    parsed = dict(zip(args[::2], args[1::2], strict=True))
    required = {"--bundle-root", "--artifacts-root", "--frames-root", "--camera-path", "--colmap-root", "--output-ply"}
    allowed = required | {"--train-command", "--export-command"}
    if not required.issubset(parsed) or not set(parsed).issubset(allowed):
        raise SystemExit(
            "Usage: nerfstudio_splatfacto_backend.py --bundle-root <path> --artifacts-root <path> --frames-root <path> --camera-path <path> --colmap-root <path> --output-ply <path> [--train-command <cmd>] [--export-command <cmd>]"
        )

    return {
        "bundle_root": parsed["--bundle-root"],
        "artifacts_root": parsed["--artifacts-root"],
        "frames_root": parsed["--frames-root"],
        "camera_path": parsed["--camera-path"],
        "colmap_root": parsed["--colmap-root"],
        "output_ply": parsed["--output-ply"],
        **({"train_command": parsed["--train-command"]} if "--train-command" in parsed else {}),
        **({"export_command": parsed["--export-command"]} if "--export-command" in parsed else {}),
    }


def _resolve_command(configured_command: str | None) -> str | None:
    if not configured_command:
        return None

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)


def _run_command(command: list[str], workspace_root: Path) -> None:
    completed = run(command, capture_output=True, check=False, text=True, cwd=str(workspace_root))
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "Nerfstudio command failed."
        raise NerfstudioSplatfactoBackendError(details)


def _find_config_path(outputs_root: Path) -> Path:
    configs = sorted(outputs_root.rglob("config.yml"))
    if not configs:
        raise NerfstudioSplatfactoBackendError("Nerfstudio training did not produce config.yml.")
    return configs[-1]


def _find_exported_ply(export_root: Path) -> Path:
    ply_files = sorted(export_root.rglob("*.ply"))
    if not ply_files:
        raise NerfstudioSplatfactoBackendError("Nerfstudio export did not produce a Gaussian splat PLY.")
    return ply_files[0]


def _materialize_images(frames_root: Path, images_root: Path) -> list[str]:
    frame_names: list[str] = []
    for frame_path in sorted(frames_root.iterdir()):
        if not frame_path.is_file():
            continue
        frame_names.append(frame_path.name)
        target = images_root / frame_path.name
        if target.exists():
            continue
        try:
            symlink(frame_path, target)
        except OSError:
            copy2(frame_path, target)
    if not frame_names:
        raise NerfstudioSplatfactoBackendError("DreamNav frames root did not contain usable images.")
    return frame_names


def _materialize_colmap_dataset(colmap_root: Path, target_root: Path) -> bool:
    required_names = ("cameras.txt", "images.txt")
    source_files = [colmap_root / name for name in required_names]
    if not all(path.is_file() for path in source_files):
        return False

    for path in sorted(colmap_root.iterdir()):
        if not path.is_file():
            continue
        target = target_root / path.name
        if target.exists():
            continue
        try:
            symlink(path, target)
        except OSError:
            copy2(path, target)
    return True


if __name__ == "__main__":
    exit(main(argv[1:]))
