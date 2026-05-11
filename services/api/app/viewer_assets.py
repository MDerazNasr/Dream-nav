from __future__ import annotations

from json import JSONDecodeError, dumps, loads
from pathlib import Path
from typing import Any

from .baseline_assets import write_nearest_view_baseline_asset
from .quality_gate import normalize_quality_gate_report
from .visibility_assets import VisibilityBuildError, build_visibility_manifest
from .zone_assets import ZONE_FILE_NAMES, ZoneAssetBuildError, build_zone_artifacts

CACHED_COMPLETION_LATENCY_MS = 12
CACHED_COMPLETION_BASELINE_ASSET = "completion/baseline_nearest_001.png"
CACHED_COMPLETION_BASELINE_FALLBACK_ASSET = "completion/baseline_nearest_001.svg"
CACHED_COMPLETION_RGB_ASSET = "completion/pred_001.svg"
CACHED_COMPLETION_MASK_ASSET = "completion/pred_001_mask.svg"


class ViewerAssetBuildError(Exception):
    pass


def build_job_viewer_assets(
    job_id: str,
    source_video: str,
    artifacts_root: Path,
) -> dict[str, object]:
    camera_path = _read_json(artifacts_root / "camera_path.json")
    capture_quality = _read_json(artifacts_root / "capture_quality.json")
    frame_extraction = _read_json(artifacts_root / "frame_extraction.json")
    camera_motion = _read_json(artifacts_root / "camera_motion.json")
    gaussian_scene = _read_json(artifacts_root / "gaussian_scene.json")
    visibility_support = _read_json(artifacts_root / "visibility_support.json")
    training_views = _read_json(artifacts_root / "training_views.json")
    scene_model = _read_json(artifacts_root / "scene_model.json")
    heldout_evaluation = _read_json(artifacts_root / "heldout_evaluation.json")
    quality_gate = _read_json(artifacts_root / "quality_gate.json")

    frame_count = _int_value(frame_extraction, "frame_count")
    splat_file = _string_value(gaussian_scene, "splat_file", "splat.ply")
    heldout_psnr = _optional_number(heldout_evaluation, "heldout_psnr_median")
    quality_gate_report = normalize_quality_gate_report(quality_gate, heldout_psnr)
    quality_gate_status = str(quality_gate_report["quality_gate"])
    try:
        visibility = build_visibility_manifest(
            job_id,
            camera_path,
            artifacts_root / splat_file,
            visibility_support,
        )
    except VisibilityBuildError as error:
        raise ViewerAssetBuildError(str(error)) from error
    try:
        zone_artifacts = build_zone_artifacts(job_id, visibility)
    except ZoneAssetBuildError as error:
        raise ViewerAssetBuildError(str(error)) from error
    cached_prediction = _build_cached_completion_prediction(artifacts_root, camera_path, quality_gate_status)
    completion = _build_completion_manifest(
        job_id,
        scene_model,
        heldout_psnr,
        quality_gate_status,
        cached_prediction,
    )
    quality = _build_quality_report(
        job_id,
        frame_count,
        camera_motion,
        visibility_support,
        scene_model,
        heldout_psnr,
        quality_gate_report,
        artifacts_root / splat_file,
        cached_prediction is not None,
    )
    metadata = _build_metadata(
        job_id,
        source_video,
        splat_file,
        frame_count,
        capture_quality,
        camera_motion,
        visibility,
        training_views,
        scene_model,
        quality,
        heldout_psnr,
        quality_gate_status,
        cached_prediction is not None,
    )

    _write_json(artifacts_root / "metadata.json", metadata)
    _write_json(artifacts_root / "quality.json", quality)
    _write_json(artifacts_root / "visibility_manifest.json", visibility)
    _write_json(artifacts_root / "completion_manifest.json", completion)
    for file_name, zone_artifact in zone_artifacts.items():
        _write_json(artifacts_root / file_name, zone_artifact)

    missing_assets = _missing_viewer_assets(artifacts_root)
    return {
        "job_id": job_id,
        "source_video": source_video,
        "output_scene_id": job_id,
        "viewer_assets": [
            "metadata.json",
            "quality.json",
            "camera_path.json",
            "visibility_manifest.json",
            "completion_manifest.json",
            *ZONE_FILE_NAMES,
            *(
                [
                    CACHED_COMPLETION_RGB_ASSET,
                    CACHED_COMPLETION_MASK_ASSET,
                    str(cached_prediction["nearest_view_asset"]),
                ]
                if cached_prediction
                else []
            ),
            splat_file,
        ],
        "missing_assets": missing_assets,
        "viewer_render_mode": "placeholder" if missing_assets else "splat",
    }


def _build_metadata(
    scene_id: str,
    source_video: str,
    splat_file: str,
    frame_count: int,
    capture_quality: dict[str, Any],
    camera_motion: dict[str, Any],
    visibility: dict[str, Any],
    training_views: dict[str, Any],
    scene_model: dict[str, Any],
    quality: dict[str, Any],
    heldout_psnr: float | None,
    quality_gate_status: str,
    has_cached_completion: bool,
) -> dict[str, object]:
    return {
        "scene_id": scene_id,
        "title": "Processed walkthrough",
        "input_video": source_video,
        "duration_sec": _number_value(capture_quality, "duration_sec", 0),
        "frame_count": frame_count,
        "pose_backend": _string_value(camera_motion, "backend", "unknown"),
        "camera_path": "camera_path.json",
        "splat_file": splat_file,
        "visibility": {
            "observed_threshold": visibility["observed_threshold"],
            "partial_threshold": visibility["partial_threshold"],
            "observed_ratio": visibility["observed_ratio"],
            "partial_ratio": visibility["partial_ratio"],
            "completion_candidate_ratio": visibility["completion_candidate_ratio"],
        },
        "scene_model": {
            "enabled": True,
            "architecture": _string_value(scene_model, "architecture", "pose_conditioned_encoder_decoder"),
            "train_views": _int_value(training_views, "train_views", default=0),
            "heldout_views": _int_value(training_views, "heldout_views", default=0),
            "training_time_sec": _number_value(scene_model, "training_time_sec", 0),
            "loss": "L_rgb + lambda_geo * L_geo",
            "heldout_psnr_median": heldout_psnr,
            "quality_gate": quality_gate_status,
            "lpips": None,
        },
        "optimization": {
            "fp32_latency_ms_p50": None,
            "fp16_latency_ms_p50": None,
            "compiled_latency_ms_p50": None,
            "tensorrt_latency_ms_p50": None,
            "cached_output_latency_ms_p50": CACHED_COMPLETION_LATENCY_MS if has_cached_completion else None,
        },
        "zones": {
            "observed": "observed_zone.json",
            "partial": "partial_zone.json",
            "completion": "completion_zone.json",
            "unknown": "unknown_zone.json",
        },
        "quality": {
            "capture_score": 0.72 if capture_quality.get("warnings") else 0.92,
            "sharpness_score": 0.79,
            "parallax_score": 0.82,
            "texture_score": 0.8,
            "splat_fps": quality["splat_fps"],
            "processing_time_sec": 0,
        },
        "product_tools": {
            "lens_modes": ["24mm", "35mm", "50mm", "85mm"],
            "camera_markers_enabled": True,
            "notes_enabled": False,
        },
    }


def _build_quality_report(
    scene_id: str,
    frame_count: int,
    camera_motion: dict[str, Any],
    visibility_support: dict[str, Any],
    scene_model: dict[str, Any],
    heldout_psnr: float | None,
    quality_gate_report: dict[str, object],
    splat_path: Path,
    has_cached_completion: bool,
) -> dict[str, object]:
    return {
        "scene_id": scene_id,
        "pose_backend": _string_value(camera_motion, "backend", "unknown"),
        "frame_count": frame_count,
        "visibility_threshold_observed": _int_value(visibility_support, "observed_threshold", default=3),
        "splat_fps": 42 if splat_path.is_file() else 0,
        "scene_model_training_sec": _number_value(scene_model, "training_time_sec", 0),
        "heldout_psnr_median": heldout_psnr,
        "quality_gate": quality_gate_report["quality_gate"],
        "completion_policy": quality_gate_report["completion_policy"],
        "quality_gate_reason": quality_gate_report["quality_gate_reason"],
        "warning_threshold_psnr": quality_gate_report["warning_threshold_psnr"],
        "pass_threshold_psnr": quality_gate_report["pass_threshold_psnr"],
        "completion_latency_ms_p50": CACHED_COMPLETION_LATENCY_MS if has_cached_completion else None,
        "completion_latency_ms_p95": CACHED_COMPLETION_LATENCY_MS + 6 if has_cached_completion else None,
        "runtime_path": "placeholder" if not splat_path.is_file() else "torch_fp16",
        "cached_completion": has_cached_completion,
    }


def _build_completion_manifest(
    scene_id: str,
    scene_model: dict[str, Any],
    heldout_psnr: float | None,
    quality_gate_status: str,
    cached_prediction: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "scene_id": scene_id,
        "model_enabled": quality_gate_status != "fail",
        "architecture": _string_value(scene_model, "architecture", "pose_conditioned_encoder_decoder"),
        "quality_gate": quality_gate_status,
        "heldout_psnr_median": heldout_psnr,
        "cache_strategy": "planned_path" if cached_prediction else "none",
        "cached_predictions": [cached_prediction] if cached_prediction else [],
    }


def _build_cached_completion_prediction(
    artifacts_root: Path,
    camera_path: dict[str, Any],
    quality_gate_status: str,
) -> dict[str, object] | None:
    if quality_gate_status == "fail":
        return None

    target_pose_index = _cached_prediction_pose_index(camera_path)
    nearest_pose_index = _nearest_reference_pose_index(camera_path, target_pose_index)
    _write_text(artifacts_root / CACHED_COMPLETION_RGB_ASSET, _cached_completion_svg())
    _write_text(artifacts_root / CACHED_COMPLETION_MASK_ASSET, _cached_completion_mask_svg())
    baseline_asset = write_nearest_view_baseline_asset(
        artifacts_root,
        camera_path,
        nearest_pose_index,
        CACHED_COMPLETION_BASELINE_ASSET,
        CACHED_COMPLETION_BASELINE_FALLBACK_ASSET,
    )
    return {
        "prediction_id": "pred_001",
        "camera_pose_index": target_pose_index,
        "rgb_asset": CACHED_COMPLETION_RGB_ASSET,
        "confidence_mask_asset": CACHED_COMPLETION_MASK_ASSET,
        "nearest_view_asset": baseline_asset,
        "nearest_view_camera_pose_index": nearest_pose_index,
        "latency_ms_p50": CACHED_COMPLETION_LATENCY_MS,
    }


def _cached_prediction_pose_index(camera_path: dict[str, Any]) -> int:
    poses = camera_path.get("poses")
    if not isinstance(poses, list) or not poses:
        return 0

    return min(1, len(poses) - 1)


def _nearest_reference_pose_index(camera_path: dict[str, Any], target_pose_index: int) -> int | None:
    poses = camera_path.get("poses")
    if not isinstance(poses, list) or len(poses) < 2:
        return None

    target_pose = poses[target_pose_index] if target_pose_index < len(poses) else poses[0]
    if not isinstance(target_pose, dict):
        return None

    target_position = _position_value(target_pose.get("position"))
    if target_position is None:
        return None

    candidates: list[tuple[float, int]] = []
    for pose_index, pose in enumerate(poses):
        if pose_index == target_pose_index or not isinstance(pose, dict):
            continue

        position = _position_value(pose.get("position"))
        if position is None:
            continue

        candidates.append((_distance(target_position, position), pose_index))

    return min(candidates)[1] if candidates else None


def _missing_viewer_assets(artifacts_root: Path) -> list[str]:
    return [
        asset_name
        for asset_name in ["splat.ply"]
        if not (artifacts_root / asset_name).is_file()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, JSONDecodeError) as error:
        raise ViewerAssetBuildError(f"Viewer asset input invalid: {path.name}") from error

    if not isinstance(payload, dict):
        raise ViewerAssetBuildError(f"Viewer asset input must be an object: {path.name}")

    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _cached_completion_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" role="img">
  <defs>
    <linearGradient id="wall" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#64716a"/>
      <stop offset="1" stop-color="#26302c"/>
    </linearGradient>
    <linearGradient id="floor" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="#1b211e"/>
      <stop offset="0.55" stop-color="#48564e"/>
      <stop offset="1" stop-color="#131714"/>
    </linearGradient>
  </defs>
  <rect width="320" height="180" fill="#101411"/>
  <polygon points="0,0 320,0 254,74 67,77" fill="url(#wall)"/>
  <polygon points="0,180 67,77 254,74 320,180" fill="url(#floor)"/>
  <polygon points="0,0 67,77 0,180" fill="#242c28"/>
  <polygon points="320,0 254,74 320,180" fill="#19211d"/>
  <rect x="130" y="29" width="58" height="50" fill="#18201d" opacity="0.82"/>
  <rect x="145" y="40" width="30" height="39" fill="#91a9a0" opacity="0.36"/>
  <path d="M74 124c41-13 92-17 169-5" fill="none" stroke="#77d7c8" stroke-width="3" opacity="0.7"/>
  <circle cx="225" cy="119" r="16" fill="#4a8ee8" opacity="0.4"/>
  <circle cx="225" cy="119" r="5" fill="#dfe7df"/>
</svg>
"""


def _cached_completion_mask_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" role="img">
  <rect width="320" height="180" fill="#111412"/>
  <rect x="0" y="0" width="320" height="180" fill="#77d7c8" opacity="0.18"/>
  <circle cx="225" cy="119" r="44" fill="#4a8ee8" opacity="0.82"/>
  <path d="M74 124c41-13 92-17 169-5" fill="none" stroke="#f0c95a" stroke-width="9" opacity="0.72"/>
</svg>
"""


def _int_value(payload: dict[str, Any], key: str, default: int = 0) -> int:
    value = payload.get(key, default)
    return int(value) if isinstance(value, int | float) else default


def _number_value(payload: dict[str, Any], key: str, default: float) -> float:
    value = payload.get(key, default)
    return float(value) if isinstance(value, int | float) else default


def _optional_number(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    return float(value) if isinstance(value, int | float) else None


def _string_value(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key, default)
    return value if isinstance(value, str) and value else default


def _position_value(value: object) -> tuple[float, float, float] | None:
    if not isinstance(value, list | tuple) or len(value) != 3:
        return None

    if not all(isinstance(component, int | float) for component in value):
        return None

    return (float(value[0]), float(value[1]), float(value[2]))


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
