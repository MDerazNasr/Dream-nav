from __future__ import annotations

from json import JSONDecodeError, dumps, loads
from pathlib import Path
from typing import Any


class SceneCompletionModelError(Exception):
    pass


def train_scene_completion_model(
    job_id: str,
    source_video: str,
    artifacts_root: Path,
) -> dict[str, object]:
    dataset = _read_json(artifacts_root / "completion_dataset.json")
    examples = _examples(dataset)
    train_examples = [example for example in examples if example["split"] == "train"]
    heldout_examples = [example for example in examples if example["split"] == "heldout"]

    if not train_examples:
        raise SceneCompletionModelError("Scene completion model requires train examples.")

    channel_mean = _channel_mean(train_examples, artifacts_root)
    train_loss = _mean_rgb_l1_loss(train_examples, artifacts_root, channel_mean)
    heldout_loss = _mean_rgb_l1_loss(heldout_examples, artifacts_root, channel_mean) if heldout_examples else None
    model = {
        "job_id": job_id,
        "source_video": source_video,
        "scene_id": job_id,
        "model_version": "scene_completion_mean_rgb_v1",
        "architecture": "pose_conditioned_encoder_decoder_stub",
        "dataset_manifest": "completion_dataset.json",
        "input_features": ["pose_encoding", "nearest_reference_rgb"],
        "output": "rgb_prediction",
        "train_examples": len(train_examples),
        "heldout_examples": len(heldout_examples),
        "rgb_channel_mean": channel_mean,
        "pose_bias": _pose_bias(train_examples),
        "train_rgb_l1": train_loss,
        "heldout_rgb_l1": heldout_loss,
    }
    _write_json(artifacts_root / "scene_model_weights.json", model)

    return {
        "job_id": job_id,
        "source_video": source_video,
        "model_artifact": "scene_model_weights.json",
        "model_version": model["model_version"],
        "architecture": model["architecture"],
        "dataset_manifest": model["dataset_manifest"],
        "train_examples": model["train_examples"],
        "heldout_examples": model["heldout_examples"],
        "train_rgb_l1": model["train_rgb_l1"],
        "heldout_rgb_l1": model["heldout_rgb_l1"],
    }


def _examples(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    examples = dataset.get("examples")
    if not isinstance(examples, list) or not examples:
        raise SceneCompletionModelError("Completion dataset did not contain examples.")

    valid_examples = [example for example in examples if _valid_example(example)]
    if len(valid_examples) != len(examples):
        raise SceneCompletionModelError("Completion dataset contains invalid examples.")

    return valid_examples


def _valid_example(example: object) -> bool:
    if not isinstance(example, dict):
        return False

    return (
        example.get("split") in {"train", "heldout"}
        and isinstance(example.get("rgb_path"), str)
        and isinstance(example.get("pose_encoding"), list)
    )


def _channel_mean(examples: list[dict[str, Any]], artifacts_root: Path) -> list[float]:
    totals = [0, 0, 0]
    count = 0
    for example in examples:
        pixels = _read_ppm_pixels(artifacts_root / example["rgb_path"])
        for red, green, blue in pixels:
            totals[0] += red
            totals[1] += green
            totals[2] += blue
            count += 1

    if count == 0:
        raise SceneCompletionModelError("Scene completion model found no RGB pixels.")

    return [round(total / count / 255, 6) for total in totals]


def _mean_rgb_l1_loss(
    examples: list[dict[str, Any]],
    artifacts_root: Path,
    channel_mean: list[float],
) -> float | None:
    if not examples:
        return None

    total_loss = 0.0
    count = 0
    target = [value * 255 for value in channel_mean]
    for example in examples:
        for pixel in _read_ppm_pixels(artifacts_root / example["rgb_path"]):
            total_loss += sum(abs(pixel[index] - target[index]) for index in range(3)) / 3 / 255
            count += 1

    return round(total_loss / max(1, count), 6)


def _pose_bias(examples: list[dict[str, Any]]) -> list[float]:
    encoding_length = max(len(example["pose_encoding"]) for example in examples)
    means = []
    for index in range(encoding_length):
        values = [
            float(example["pose_encoding"][index])
            for example in examples
            if index < len(example["pose_encoding"])
        ]
        means.append(round(sum(values) / max(1, len(values)), 6))

    return means


def _read_ppm_pixels(path: Path) -> list[tuple[int, int, int]]:
    try:
        tokens = path.read_text(encoding="ascii").split()
    except FileNotFoundError as error:
        raise SceneCompletionModelError(f"Scene model RGB input missing: {path.name}") from error

    if len(tokens) < 4 or tokens[0] != "P3":
        raise SceneCompletionModelError(f"Scene model RGB input is not a PPM P3 file: {path.name}")

    values = [int(token) for token in tokens[4:]]
    if len(values) % 3 != 0:
        raise SceneCompletionModelError(f"Scene model RGB input has incomplete pixels: {path.name}")

    return [
        (values[index], values[index + 1], values[index + 2])
        for index in range(0, len(values), 3)
    ]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, JSONDecodeError) as error:
        raise SceneCompletionModelError(f"Scene model input invalid: {path.name}") from error

    if not isinstance(payload, dict):
        raise SceneCompletionModelError(f"Scene model input must be an object: {path.name}")

    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(dumps(payload, indent=2), encoding="utf-8")
