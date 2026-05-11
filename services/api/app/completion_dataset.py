from __future__ import annotations

from json import JSONDecodeError, dumps, loads
from math import sqrt
from pathlib import Path
from typing import Any


class CompletionDatasetError(Exception):
    pass


def build_completion_dataset(
    job_id: str,
    source_video: str,
    artifacts_root: Path,
) -> dict[str, object]:
    pseudo_views = _read_json(artifacts_root / "pseudo_views.json")
    views = _views(pseudo_views)
    examples = [_example(view, views, artifacts_root) for view in views]
    train_examples = [example for example in examples if example["split"] == "train"]
    heldout_examples = [example for example in examples if example["split"] == "heldout"]

    if not train_examples:
        raise CompletionDatasetError("Completion dataset requires at least one train view.")

    if not heldout_examples:
        raise CompletionDatasetError("Completion dataset requires at least one heldout view.")

    manifest = {
        "job_id": job_id,
        "source_video": source_video,
        "scene_id": job_id,
        "dataset_version": "completion_dataset_v1",
        "source_manifest": "pseudo_views.json",
        "pose_encoding": "position_rotation_fov_v1",
        "reference_strategy": "nearest_train_views_v1",
        "train_examples": len(train_examples),
        "heldout_examples": len(heldout_examples),
        "examples": examples,
    }
    _write_json(artifacts_root / "completion_dataset.json", manifest)

    return {
        "job_id": job_id,
        "source_video": source_video,
        "dataset_manifest": "completion_dataset.json",
        "dataset_version": manifest["dataset_version"],
        "pose_encoding": manifest["pose_encoding"],
        "reference_strategy": manifest["reference_strategy"],
        "train_examples": manifest["train_examples"],
        "heldout_examples": manifest["heldout_examples"],
    }


def _example(
    view: dict[str, Any],
    views: list[dict[str, Any]],
    artifacts_root: Path,
) -> dict[str, object]:
    rgb_path = _asset_path(view, "rgb_path", artifacts_root)
    depth_path = _asset_path(view, "depth_path", artifacts_root)
    target_pose = _target_pose(view)
    references = _references(view, views)
    return {
        "example_id": view["view_id"],
        "split": view["split"],
        "rgb_path": rgb_path,
        "depth_path": depth_path,
        "target_pose": target_pose,
        "pose_encoding": _pose_encoding(target_pose),
        "references": references,
    }


def _references(view: dict[str, Any], views: list[dict[str, Any]]) -> list[dict[str, object]]:
    target_position = _target_pose(view)["position"]
    candidates = [candidate for candidate in views if candidate["split"] == "train"]
    if len(candidates) > 1:
        candidates = [candidate for candidate in candidates if candidate["view_id"] != view["view_id"]]

    ranked = sorted(candidates, key=lambda candidate: _distance(target_position, _target_pose(candidate)["position"]))
    references = []
    for candidate in ranked[:2]:
        candidate_pose = _target_pose(candidate)
        references.append(
            {
                "view_id": candidate["view_id"],
                "relative_position": _relative_position(target_position, candidate_pose["position"]),
                "distance_meters": round(_distance(target_position, candidate_pose["position"]), 4),
            }
        )

    return references


def _views(pseudo_views: dict[str, Any]) -> list[dict[str, Any]]:
    views = pseudo_views.get("views")
    if not isinstance(views, list) or not views:
        raise CompletionDatasetError("Pseudo-view manifest did not contain views.")

    valid_views = [view for view in views if _valid_view(view)]
    if len(valid_views) != len(views):
        raise CompletionDatasetError("Pseudo-view manifest contains invalid view records.")

    return valid_views


def _valid_view(view: object) -> bool:
    if not isinstance(view, dict):
        return False

    return (
        isinstance(view.get("view_id"), str)
        and view.get("split") in {"train", "heldout"}
        and isinstance(view.get("rgb_path"), str)
        and isinstance(view.get("depth_path"), str)
        and _valid_target_pose(view.get("target_pose"))
    )


def _valid_target_pose(target_pose: object) -> bool:
    if not isinstance(target_pose, dict):
        return False

    position = target_pose.get("position")
    rotation = target_pose.get("rotation_xyzw")
    return (
        isinstance(position, list)
        and len(position) == 3
        and isinstance(rotation, list)
        and len(rotation) == 4
        and isinstance(target_pose.get("fov_degrees"), int | float)
    )


def _target_pose(view: dict[str, Any]) -> dict[str, Any]:
    target_pose = view["target_pose"]
    if not isinstance(target_pose, dict):
        raise CompletionDatasetError("Pseudo-view target pose is invalid.")

    return target_pose


def _pose_encoding(target_pose: dict[str, Any]) -> list[float]:
    position = target_pose["position"]
    rotation = target_pose["rotation_xyzw"]
    return [
        round(float(position[0]), 5),
        round(float(position[1]), 5),
        round(float(position[2]), 5),
        round(float(rotation[0]), 5),
        round(float(rotation[1]), 5),
        round(float(rotation[2]), 5),
        round(float(rotation[3]), 5),
        round(float(target_pose["fov_degrees"]) / 180, 5),
    ]


def _asset_path(view: dict[str, Any], key: str, artifacts_root: Path) -> str:
    value = view[key]
    if not isinstance(value, str):
        raise CompletionDatasetError(f"Pseudo-view {key} must be a string.")

    path = artifacts_root / value
    if not path.is_file():
        raise CompletionDatasetError(f"Pseudo-view asset missing: {value}")

    return value


def _relative_position(target_position: list[object], reference_position: list[object]) -> list[float]:
    return [
        round(float(reference_position[0]) - float(target_position[0]), 4),
        round(float(reference_position[1]) - float(target_position[1]), 4),
        round(float(reference_position[2]) - float(target_position[2]), 4),
    ]


def _distance(first_position: list[object], second_position: list[object]) -> float:
    return sqrt(
        (float(first_position[0]) - float(second_position[0])) ** 2
        + (float(first_position[1]) - float(second_position[1])) ** 2
        + (float(first_position[2]) - float(second_position[2])) ** 2
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, JSONDecodeError) as error:
        raise CompletionDatasetError(f"Completion dataset input invalid: {path.name}") from error

    if not isinstance(payload, dict):
        raise CompletionDatasetError(f"Completion dataset input must be an object: {path.name}")

    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(dumps(payload, indent=2), encoding="utf-8")
