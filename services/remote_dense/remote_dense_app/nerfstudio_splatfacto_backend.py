#!/usr/bin/env python3

from __future__ import annotations

from os import environ, symlink
from pathlib import Path
from shutil import copy2, which
from subprocess import run
from sys import argv, exit
from math import acos, sqrt

try:
    from remote_dense_app.nerfstudio_backend_error import NerfstudioSplatfactoBackendError
    from remote_dense_app.nerfstudio_diagnostics import render_dataset_diagnostics
    from remote_dense_app.nerfstudio_dataset_writer import (
        colmap_applied_transform,
        write_sparse_point_cloud,
        write_transforms,
    )
except ModuleNotFoundError:
    from nerfstudio_backend_error import NerfstudioSplatfactoBackendError
    from nerfstudio_diagnostics import render_dataset_diagnostics
    from nerfstudio_dataset_writer import (
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
    if using_official_colmap and environ.get("DREAMNAV_NERFSTUDIO_ENABLE_COLLIDER", "False").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        # Nerfstudio applies args to the preceding subcommand, so model flags must stay
        # attached to the method section rather than the trailing dataparser subcommand.
        train_args.extend(
            [
                "--pipeline.model.enable-collider",
                "False",
            ]
        )
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

    if _diagnostics_enabled():
        _maybe_render_dataset_diagnostics(workspace_root)

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

    minimum_support = _configured_minimum_colmap_support()
    if (minimum_support > 0 or _consecutive_dedupe_enabled()) and (colmap_root / "points3D.txt").is_file():
        retained_count = _write_filtered_colmap_dataset(colmap_root, target_root, minimum_support)
        if retained_count is not None:
            return True

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


def _configured_minimum_colmap_support() -> int:
    raw_value = environ.get("DREAMNAV_NERFSTUDIO_MIN_IMAGE_POINT_SUPPORT", "300").strip()
    try:
        return max(0, int(raw_value))
    except ValueError:
        return 300


def _configured_minimum_retained_images() -> int:
    raw_value = environ.get("DREAMNAV_NERFSTUDIO_MIN_RETAINED_IMAGES", "24").strip()
    try:
        return max(1, int(raw_value))
    except ValueError:
        return 24


def _configured_minimum_translation_delta() -> float:
    raw_value = environ.get("DREAMNAV_NERFSTUDIO_MIN_TRANSLATION_DELTA", "0.05").strip()
    try:
        return max(0.0, float(raw_value))
    except ValueError:
        return 0.05


def _configured_minimum_rotation_delta_degrees() -> float:
    raw_value = environ.get("DREAMNAV_NERFSTUDIO_MIN_ROTATION_DELTA_DEGREES", "2.0").strip()
    try:
        return max(0.0, float(raw_value))
    except ValueError:
        return 2.0


def _consecutive_dedupe_enabled() -> bool:
    return _configured_minimum_translation_delta() > 0.0 or _configured_minimum_rotation_delta_degrees() > 0.0


def _diagnostics_enabled() -> bool:
    return environ.get("DREAMNAV_NERFSTUDIO_ENABLE_DIAGNOSTICS", "1").lower() not in {"0", "false", "no", "off"}


def _diagnostics_sample_count() -> int:
    raw_value = environ.get("DREAMNAV_NERFSTUDIO_DIAGNOSTIC_SAMPLE_COUNT", "6").strip()
    try:
        return max(1, int(raw_value))
    except ValueError:
        return 6


def _maybe_render_dataset_diagnostics(workspace_root: Path) -> None:
    diagnostics_root = workspace_root / "diagnostics"
    try:
        render_dataset_diagnostics(
            workspace_root=workspace_root,
            output_root=diagnostics_root,
            render_command=environ.get("DREAMNAV_NERFSTUDIO_RENDER_COMMAND") or "ns-render",
            sample_count=_diagnostics_sample_count(),
        )
    except Exception:
        if environ.get("DREAMNAV_NERFSTUDIO_REQUIRE_DIAGNOSTICS", "0").lower() in {"1", "true", "yes", "on"}:
            raise


def _write_filtered_colmap_dataset(colmap_root: Path, target_root: Path, minimum_support: int) -> int | None:
    images_path = colmap_root / "images.txt"
    points_path = colmap_root / "points3D.txt"
    if not images_path.is_file() or not points_path.is_file():
        return None

    image_entries, image_comments = _parse_colmap_images(images_path)
    if not image_entries:
        return None

    selected_entries = [entry for entry in image_entries if entry["support_count"] >= minimum_support]
    minimum_retained = _configured_minimum_retained_images()
    if len(selected_entries) < minimum_retained:
        return None
    deduped_entries = _dedupe_consecutive_entries(selected_entries)
    if len(deduped_entries) >= minimum_retained:
        selected_entries = deduped_entries
    if len(selected_entries) == len(image_entries):
        return None

    selected_image_ids = {entry["image_id"] for entry in selected_entries}

    for path in sorted(colmap_root.iterdir()):
        if not path.is_file():
            continue
        target = target_root / path.name
        if target.exists():
            continue
        if path.name in {"images.txt", "points3D.txt"}:
            continue
        try:
            symlink(path, target)
        except OSError:
            copy2(path, target)

    cameras_path = colmap_root / "cameras.txt"
    cameras_target = target_root / "cameras.txt"
    if cameras_path.is_file() and not cameras_target.exists():
        try:
            symlink(cameras_path, cameras_target)
        except OSError:
            copy2(cameras_path, cameras_target)

    filtered_images = [line for line in image_comments]
    filtered_images.append(
        f"# DreamNav filtered images with support >= {minimum_support}; retained {len(selected_entries)} / {len(image_entries)}"
    )
    for entry in selected_entries:
        filtered_images.append(entry["image_line"])
        filtered_images.append(entry["points_line"])
    (target_root / "images.txt").write_text("\n".join(filtered_images) + "\n", encoding="utf-8")

    point_comments, filtered_points = _filter_colmap_points(points_path, selected_image_ids)
    (target_root / "points3D.txt").write_text("\n".join([*point_comments, *filtered_points]) + "\n", encoding="utf-8")
    return len(selected_entries)


def _parse_colmap_images(images_path: Path) -> tuple[list[dict[str, object]], list[str]]:
    comments: list[str] = []
    entries: list[dict[str, object]] = []
    lines = images_path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("#"):
            comments.append(raw_line)
            index += 1
            continue
        parts = stripped.split()
        if len(parts) < 10:
            raise NerfstudioSplatfactoBackendError("COLMAP images.txt contains a malformed image row.")
        if index + 1 >= len(lines):
            raise NerfstudioSplatfactoBackendError("COLMAP images.txt is missing a points row.")
        quaternion = tuple(float(component) for component in parts[1:5])
        translation = tuple(float(component) for component in parts[5:8])
        points_line = lines[index + 1].strip()
        point_tokens = points_line.split()
        support_count = sum(1 for token_index in range(2, len(point_tokens), 3) if point_tokens[token_index] != "-1")
        entries.append(
            {
                "image_id": int(parts[0]),
                "image_name": Path(parts[9]).name,
                "image_line": raw_line,
                "points_line": lines[index + 1],
                "support_count": support_count,
                "camera_center": _camera_center(quaternion, translation),
                "quaternion_wxyz": quaternion,
            }
        )
        index += 2
    return entries, comments


def _filter_colmap_points(points_path: Path, selected_image_ids: set[int]) -> tuple[list[str], list[str]]:
    comments: list[str] = []
    filtered_lines: list[str] = []
    for raw_line in points_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            comments.append(raw_line)
            continue
        parts = stripped.split()
        if len(parts) < 8:
            raise NerfstudioSplatfactoBackendError("COLMAP points3D.txt contains a malformed point row.")
        track = parts[8:]
        retained_track: list[str] = []
        for index in range(0, len(track), 2):
            if index + 1 >= len(track):
                break
            image_id = int(track[index])
            if image_id in selected_image_ids:
                retained_track.extend([track[index], track[index + 1]])
        if len(retained_track) < 4:
            continue
        filtered_lines.append(" ".join(parts[:8] + retained_track))
    return comments, filtered_lines


def _dedupe_consecutive_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    minimum_translation = _configured_minimum_translation_delta()
    minimum_rotation_degrees = _configured_minimum_rotation_delta_degrees()
    if minimum_translation <= 0.0 and minimum_rotation_degrees <= 0.0:
        return entries

    deduped: list[dict[str, object]] = []
    previous_retained: dict[str, object] | None = None
    for entry in entries:
        if previous_retained is None:
            deduped.append(entry)
            previous_retained = entry
            continue
        translation_delta = _distance(
            previous_retained["camera_center"],  # type: ignore[arg-type]
            entry["camera_center"],  # type: ignore[arg-type]
        )
        rotation_delta = _quaternion_angle_degrees(
            previous_retained["quaternion_wxyz"],  # type: ignore[arg-type]
            entry["quaternion_wxyz"],  # type: ignore[arg-type]
        )
        if translation_delta < minimum_translation and rotation_delta < minimum_rotation_degrees:
            continue
        deduped.append(entry)
        previous_retained = entry
    return deduped


def _distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def _quaternion_angle_degrees(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> float:
    dot = abs(sum(left[index] * right[index] for index in range(4)))
    clamped = min(1.0, max(-1.0, dot))
    return 2.0 * acos(clamped) * (180.0 / 3.141592653589793)


def _camera_center(
    quaternion_wxyz: tuple[float, float, float, float],
    translation_xyz: tuple[float, float, float],
) -> tuple[float, float, float]:
    qw, qx, qy, qz = quaternion_wxyz
    tx, ty, tz = translation_xyz
    rotation = (
        (1 - 2 * qy * qy - 2 * qz * qz, 2 * qx * qy - 2 * qz * qw, 2 * qx * qz + 2 * qy * qw),
        (2 * qx * qy + 2 * qz * qw, 1 - 2 * qx * qx - 2 * qz * qz, 2 * qy * qz - 2 * qx * qw),
        (2 * qx * qz - 2 * qy * qw, 2 * qy * qz + 2 * qx * qw, 1 - 2 * qx * qx - 2 * qy * qy),
    )
    return (
        -(rotation[0][0] * tx + rotation[1][0] * ty + rotation[2][0] * tz),
        -(rotation[0][1] * tx + rotation[1][1] * ty + rotation[2][1] * tz),
        -(rotation[0][2] * tx + rotation[1][2] * ty + rotation[2][2] * tz),
    )


if __name__ == "__main__":
    exit(main(argv[1:]))
