#!/usr/bin/env python3

from __future__ import annotations

from json import JSONDecodeError, dumps, loads
from math import sqrt
from os import environ, symlink
from pathlib import Path
from shutil import copy2, which
from subprocess import run
from sys import argv, exit


class NerfstudioSplatfactoBackendError(Exception):
    pass


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
    outputs_root = workspace_root / "outputs"
    export_root = workspace_root / "export"
    images_root.mkdir(parents=True, exist_ok=True)
    outputs_root.mkdir(parents=True, exist_ok=True)
    export_root.mkdir(parents=True, exist_ok=True)

    frame_names = _materialize_images(frames_root, images_root)
    sparse_point_cloud = _write_sparse_point_cloud(colmap_root, dataset_root / "sparse_pc.ply")
    _write_transforms(camera_path, dataset_root / "transforms.json", frame_names, sparse_point_cloud)

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

    train_help = run(
        [resolved_train, environ.get("DREAMNAV_NERFSTUDIO_METHOD", "splatfacto"), "--help"],
        capture_output=True,
        check=False,
        text=True,
    )
    export_help = run(
        [resolved_export, "gaussian-splat", "--help"],
        capture_output=True,
        check=False,
        text=True,
    )
    if train_help.returncode != 0:
        return False, train_help.stderr.strip() or train_help.stdout.strip() or "Nerfstudio train command failed health check."
    if export_help.returncode != 0:
        return False, export_help.stderr.strip() or export_help.stdout.strip() or "Nerfstudio export command failed health check."
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


def _write_transforms(
    camera_path: Path,
    transforms_path: Path,
    frame_names: list[str],
    sparse_point_cloud: Path | None,
) -> None:
    try:
        payload = loads(camera_path.read_text(encoding="utf-8"))
    except JSONDecodeError as error:
        raise NerfstudioSplatfactoBackendError("DreamNav camera path is invalid.") from error

    intrinsics = payload.get("intrinsics")
    poses = payload.get("poses")
    if not isinstance(intrinsics, dict) or not isinstance(poses, list):
        raise NerfstudioSplatfactoBackendError("DreamNav camera path is missing intrinsics or poses.")

    transforms = {
        "camera_model": "OPENCV",
        "fl_x": float(intrinsics["fx"]),
        "fl_y": float(intrinsics["fy"]),
        "cx": float(intrinsics["cx"]),
        "cy": float(intrinsics["cy"]),
        "w": int(intrinsics["width"]),
        "h": int(intrinsics["height"]),
        "frames": _frames_payload(poses, frame_names),
    }
    if sparse_point_cloud is not None:
        transforms["ply_file_path"] = sparse_point_cloud.name
    if not transforms["frames"]:
        raise NerfstudioSplatfactoBackendError("DreamNav camera path did not contain usable poses.")

    transforms_path.write_text(dumps(transforms, indent=2), encoding="utf-8")


def _frames_payload(poses: list[object], frame_names: list[str]) -> list[dict[str, object]]:
    frames = []
    for pose in poses:
        if not isinstance(pose, dict) or "frame_index" not in pose or "position" not in pose or "rotation_xyzw" not in pose:
            continue
        frame_index = int(pose["frame_index"])
        if frame_index < 0 or frame_index >= len(frame_names):
            raise NerfstudioSplatfactoBackendError("DreamNav camera path frame index did not match extracted frames.")
        frames.append(
            {
                "file_path": f"images/{frame_names[frame_index]}",
                "transform_matrix": _transform_matrix(pose["position"], pose["rotation_xyzw"]),
            }
        )
    return frames


def _write_sparse_point_cloud(colmap_root: Path, sparse_point_cloud_path: Path) -> Path | None:
    points = _read_colmap_sparse_points(colmap_root)
    if not points:
        return None

    header = "\n".join(
        [
            "ply",
            "format ascii 1.0",
            f"element vertex {len(points)}",
            "property float x",
            "property float y",
            "property float z",
            "property uchar red",
            "property uchar green",
            "property uchar blue",
            "end_header",
        ]
    )
    payload = "\n".join(
        f"{x} {y} {z} {r} {g} {b}"
        for x, y, z, r, g, b in points
    )
    sparse_point_cloud_path.write_text(f"{header}\n{payload}\n", encoding="utf-8")
    return sparse_point_cloud_path


def _read_colmap_sparse_points(colmap_root: Path) -> list[tuple[float, float, float, int, int, int]]:
    for candidate in (
        colmap_root / "points3D.txt",
        colmap_root / "sparse" / "0" / "points3D.txt",
    ):
        if candidate.is_file():
            return _parse_points3d(candidate)
    return []


def _parse_points3d(points3d_path: Path) -> list[tuple[float, float, float, int, int, int]]:
    points: list[tuple[float, float, float, int, int, int]] = []
    for line in points3d_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 7:
            continue
        try:
            points.append(
                (
                    float(parts[1]),
                    float(parts[2]),
                    float(parts[3]),
                    int(parts[4]),
                    int(parts[5]),
                    int(parts[6]),
                )
            )
        except ValueError:
            continue
    return points


def _transform_matrix(position: object, rotation_xyzw: object) -> list[list[float]]:
    if not isinstance(position, list) or len(position) != 3:
        raise NerfstudioSplatfactoBackendError("Camera pose position is invalid.")
    if not isinstance(rotation_xyzw, list) or len(rotation_xyzw) != 4:
        raise NerfstudioSplatfactoBackendError("Camera pose rotation is invalid.")

    x, y, z, w = [float(value) for value in rotation_xyzw]
    length = sqrt((x * x) + (y * y) + (z * z) + (w * w))
    if length <= 1e-8:
        raise NerfstudioSplatfactoBackendError("Camera pose rotation is invalid.")
    x, y, z, w = [value / length for value in (x, y, z, w)]

    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    return [
        [1 - (2 * (yy + zz)), 2 * (xy - wz), 2 * (xz + wy), float(position[0])],
        [2 * (xy + wz), 1 - (2 * (xx + zz)), 2 * (yz - wx), float(position[1])],
        [2 * (xz - wy), 2 * (yz + wx), 1 - (2 * (xx + yy)), float(position[2])],
        [0.0, 0.0, 0.0, 1.0],
    ]


if __name__ == "__main__":
    exit(main(argv[1:]))
