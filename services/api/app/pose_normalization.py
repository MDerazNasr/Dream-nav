from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path

COORDINATE_SYSTEM = "dreamnav_viewer_v1"
DEFAULT_FOV_DEGREES = 60


class PoseNormalizationError(Exception):
    pass


@dataclass(frozen=True)
class CameraIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float


@dataclass(frozen=True)
class RawPose:
    frame_index: int
    frame_name: str
    timestamp_sec: float
    position: tuple[float, float, float]
    rotation_xyzw: tuple[float, float, float, float]
    fov_degrees: float = DEFAULT_FOV_DEGREES


def normalize_camera_path(
    scene_id: str,
    raw_poses: list[RawPose],
    intrinsics: CameraIntrinsics | None = None,
) -> dict[str, object]:
    if not raw_poses:
        raise PoseNormalizationError("Camera pose normalization requires at least one pose.")

    normalized_intrinsics = intrinsics or CameraIntrinsics(
        width=1920,
        height=1080,
        fx=1240,
        fy=1240,
        cx=960,
        cy=540,
    )

    return {
        "scene_id": scene_id,
        "coordinate_system": COORDINATE_SYSTEM,
        "intrinsics": _normalize_intrinsics(normalized_intrinsics),
        "poses": [_normalize_pose(raw_pose) for raw_pose in raw_poses],
    }


def stub_raw_poses_from_frames(frames: list[Path], frame_rate: float) -> list[RawPose]:
    if not frames:
        raise PoseNormalizationError("Camera pose normalization requires extracted frames.")

    if frame_rate <= 0:
        raise PoseNormalizationError("Frame rate must be greater than zero for pose normalization.")

    return [
        RawPose(
            frame_index=index,
            frame_name=frame.name,
            timestamp_sec=index / frame_rate,
            position=(index * 0.25, 1.5, -index * 0.15),
            rotation_xyzw=(0, 0, 0, 1),
        )
        for index, frame in enumerate(frames)
    ]


def _normalize_intrinsics(intrinsics: CameraIntrinsics) -> dict[str, float | int]:
    if intrinsics.width < 1 or intrinsics.height < 1:
        raise PoseNormalizationError("Camera intrinsics dimensions must be positive.")

    values = (intrinsics.fx, intrinsics.fy, intrinsics.cx, intrinsics.cy)
    if any(value < 0 or not isfinite(value) for value in values):
        raise PoseNormalizationError("Camera intrinsics must be finite non-negative values.")

    return {
        "width": intrinsics.width,
        "height": intrinsics.height,
        "fx": intrinsics.fx,
        "fy": intrinsics.fy,
        "cx": intrinsics.cx,
        "cy": intrinsics.cy,
    }


def _normalize_pose(raw_pose: RawPose) -> dict[str, object]:
    if raw_pose.frame_index < 0:
        raise PoseNormalizationError("Pose frame index must be non-negative.")

    if raw_pose.timestamp_sec < 0 or not isfinite(raw_pose.timestamp_sec):
        raise PoseNormalizationError("Pose timestamp must be a finite non-negative value.")

    if not 1 <= raw_pose.fov_degrees <= 179:
        raise PoseNormalizationError("Pose FOV must be between 1 and 179 degrees.")

    _validate_numeric_tuple(raw_pose.position, 3, "Pose position")
    _validate_numeric_tuple(raw_pose.rotation_xyzw, 4, "Pose rotation")

    return {
        "frame_index": raw_pose.frame_index,
        "timestamp_sec": raw_pose.timestamp_sec,
        "position": list(raw_pose.position),
        "rotation_xyzw": list(raw_pose.rotation_xyzw),
        "fov_degrees": raw_pose.fov_degrees,
    }


def _validate_numeric_tuple(values: tuple[float, ...], expected_length: int, label: str) -> None:
    if len(values) != expected_length or any(not isfinite(value) for value in values):
        raise PoseNormalizationError(f"{label} must contain {expected_length} finite values.")
