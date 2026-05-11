from __future__ import annotations

from json import JSONDecodeError, dumps, loads
from pathlib import Path
from typing import Any

from .splat_assets import SplatAssetError, read_splat_points

RGB_WIDTH = 8
RGB_HEIGHT = 6
TRAIN_OFFSETS = (
    (0.0, 0.0, 0.0),
    (0.08, 0.0, -0.05),
    (-0.08, 0.0, 0.05),
)
HELDOUT_OFFSETS = (
    (0.14, 0.0, -0.12),
    (-0.14, 0.0, 0.12),
)


class PseudoViewRenderError(Exception):
    pass


def render_pseudo_views(
    job_id: str,
    source_video: str,
    artifacts_root: Path,
) -> dict[str, object]:
    camera_path = _read_json(artifacts_root / "camera_path.json")
    poses = _poses(camera_path)
    try:
        splat_points = read_splat_points(artifacts_root / "splat.ply", max_points=64)
    except SplatAssetError as error:
        raise PseudoViewRenderError(str(error)) from error

    output_root = artifacts_root / "pseudo_views"
    rgb_root = output_root / "rgb"
    depth_root = output_root / "depth"
    rgb_root.mkdir(parents=True, exist_ok=True)
    depth_root.mkdir(parents=True, exist_ok=True)

    views = _view_records(poses)
    for view in views:
        _write_rgb(rgb_root / str(view["rgb_path"]).split("/")[-1], view, splat_points)
        _write_depth(depth_root / str(view["depth_path"]).split("/")[-1], view, splat_points)

    manifest = {
        "job_id": job_id,
        "source_video": source_video,
        "scene_id": job_id,
        "renderer": "placeholder_splat_renderer_v1",
        "split_strategy": "camera_path_perturbation_v1",
        "depth_source": "splat_depth_placeholder_v1",
        "splat_file": "splat.ply",
        "camera_path": "camera_path.json",
        "rgb_size": [RGB_WIDTH, RGB_HEIGHT],
        "depth_size": [RGB_WIDTH, RGB_HEIGHT],
        "train_views": sum(1 for view in views if view["split"] == "train"),
        "heldout_views": sum(1 for view in views if view["split"] == "heldout"),
        "views": views,
    }
    _write_json(artifacts_root / "pseudo_views.json", manifest)

    return {
        "job_id": job_id,
        "source_video": source_video,
        "renderer": manifest["renderer"],
        "split_strategy": manifest["split_strategy"],
        "depth_source": manifest["depth_source"],
        "pseudo_views_manifest": "pseudo_views.json",
        "output_root": "pseudo_views",
        "rgb_format": "ppm_p3",
        "depth_format": "pgm_p2",
        "train_views": manifest["train_views"],
        "heldout_views": manifest["heldout_views"],
    }


def _view_records(poses: list[dict[str, Any]]) -> list[dict[str, object]]:
    records = []
    for pose_index, pose in enumerate(poses):
        for offset_index, offset in enumerate(TRAIN_OFFSETS):
            records.append(_view_record("train", _source_pose_index(pose, pose_index), offset_index, pose, offset))

    heldout_poses = poses if len(poses) <= 2 else [poses[0], poses[len(poses) // 2], poses[-1]]
    for heldout_index, pose in enumerate(heldout_poses):
        offset = HELDOUT_OFFSETS[heldout_index % len(HELDOUT_OFFSETS)]
        records.append(_view_record("heldout", _source_pose_index(pose, heldout_index), heldout_index, pose, offset))

    return records


def _view_record(
    split: str,
    source_pose_index: int,
    offset_index: int,
    pose: dict[str, Any],
    offset: tuple[float, float, float],
) -> dict[str, object]:
    view_id = f"{split}_pose{source_pose_index:04d}_offset{offset_index:02d}"
    position = pose["position"]
    target_position = [
        round(float(position[0]) + offset[0], 4),
        round(float(position[1]) + offset[1], 4),
        round(float(position[2]) + offset[2], 4),
    ]
    return {
        "view_id": view_id,
        "split": split,
        "source_pose_index": source_pose_index,
        "target_pose": {
            "position": target_position,
            "rotation_xyzw": pose["rotation_xyzw"],
            "fov_degrees": pose["fov_degrees"],
        },
        "rgb_path": f"pseudo_views/rgb/{view_id}.ppm",
        "depth_path": f"pseudo_views/depth/{view_id}.pgm",
    }


def _source_pose_index(pose: dict[str, Any], fallback: int) -> int:
    frame_index = pose.get("frame_index")
    return int(frame_index) if isinstance(frame_index, int | float) else fallback


def _write_rgb(path: Path, view: dict[str, object], splat_points: list[object]) -> None:
    seed = _seed(view, len(splat_points))
    lines = ["P3", f"{RGB_WIDTH} {RGB_HEIGHT}", "255"]
    for y in range(RGB_HEIGHT):
        row = []
        for x in range(RGB_WIDTH):
            row.append(f"{(seed + x * 17) % 256} {(seed + y * 29) % 256} {(seed + x * y * 7) % 256}")
        lines.append(" ".join(row))

    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _write_depth(path: Path, view: dict[str, object], splat_points: list[object]) -> None:
    seed = _seed(view, len(splat_points))
    lines = ["P2", f"{RGB_WIDTH} {RGB_HEIGHT}", "65535"]
    for y in range(RGB_HEIGHT):
        row = [str(800 + seed * 3 + x * 11 + y * 23) for x in range(RGB_WIDTH)]
        lines.append(" ".join(row))

    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _seed(view: dict[str, object], splat_count: int) -> int:
    view_id = str(view["view_id"])
    return (sum(ord(character) for character in view_id) + splat_count * 13) % 251


def _poses(camera_path: dict[str, Any]) -> list[dict[str, Any]]:
    poses = camera_path.get("poses")
    if not isinstance(poses, list):
        raise PseudoViewRenderError("Camera path poses are required before rendering pseudo-views.")

    valid_poses = [pose for pose in poses if _valid_pose(pose)]
    if not valid_poses:
        raise PseudoViewRenderError("Camera path did not contain renderable poses.")

    return valid_poses


def _valid_pose(pose: object) -> bool:
    if not isinstance(pose, dict):
        return False

    position = pose.get("position")
    rotation = pose.get("rotation_xyzw")
    return (
        isinstance(position, list)
        and len(position) == 3
        and isinstance(rotation, list)
        and len(rotation) == 4
        and isinstance(pose.get("fov_degrees"), int | float)
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, JSONDecodeError) as error:
        raise PseudoViewRenderError(f"Pseudo-view input invalid: {path.name}") from error

    if not isinstance(payload, dict):
        raise PseudoViewRenderError(f"Pseudo-view input must be an object: {path.name}")

    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(dumps(payload, indent=2), encoding="utf-8")
