from __future__ import annotations

from math import sqrt
from pathlib import Path

from .pose_normalization import CameraIntrinsics, RawPose


class ColmapPoseParseError(Exception):
    pass


def parse_colmap_text_model(
    model_root: Path,
    frames: list[Path],
    frame_rate: float,
) -> tuple[list[RawPose], CameraIntrinsics]:
    if frame_rate <= 0:
        raise ColmapPoseParseError("Frame rate must be greater than zero for COLMAP pose parsing.")

    camera_by_id = _parse_cameras(model_root / "cameras.txt")
    poses, camera_id = _parse_images(model_root / "images.txt", camera_by_id, _frame_index_by_name(frames), frame_rate)

    if len(poses) != len(frames):
        raise ColmapPoseParseError(
            f"COLMAP pose count {len(poses)} does not match extracted frame count {len(frames)}."
        )

    if not poses:
        raise ColmapPoseParseError("COLMAP output did not contain camera poses.")

    return poses, camera_by_id[camera_id].intrinsics


def _parse_cameras(cameras_path: Path) -> dict[int, "_ParsedCamera"]:
    lines = _data_lines(cameras_path, "COLMAP cameras.txt is missing.")
    cameras = {}

    for line in lines:
        parts = line.split()
        if len(parts) < 5:
            raise ColmapPoseParseError("COLMAP cameras.txt contains a malformed camera row.")

        camera_id = _parse_int(parts[0], "camera id")
        model = parts[1]
        width = _parse_int(parts[2], "camera width")
        height = _parse_int(parts[3], "camera height")
        params = [_parse_float(value, "camera parameter") for value in parts[4:]]
        cameras[camera_id] = _ParsedCamera(_camera_intrinsics(model, width, height, params))

    if not cameras:
        raise ColmapPoseParseError("COLMAP cameras.txt did not contain camera intrinsics.")

    return cameras


def _parse_images(
    images_path: Path,
    camera_by_id: dict[int, "_ParsedCamera"],
    frame_index_by_name: dict[str, int],
    frame_rate: float,
) -> tuple[list[RawPose], int]:
    lines = _image_lines(images_path)
    poses = []
    first_camera_id = None
    line_index = 0

    while line_index < len(lines):
        image_line = lines[line_index].strip()
        if not image_line:
            line_index += 1
            continue

        parts = image_line.split()
        if len(parts) < 10:
            raise ColmapPoseParseError("COLMAP images.txt contains a malformed image row.")

        qvec = tuple(_parse_float(value, "image quaternion") for value in parts[1:5])
        tvec = tuple(_parse_float(value, "image translation") for value in parts[5:8])
        camera_id = _parse_int(parts[8], "image camera id")
        image_name = parts[9]
        if camera_id not in camera_by_id:
            raise ColmapPoseParseError(f"COLMAP image {image_name} references missing camera {camera_id}.")
        if first_camera_id is None:
            first_camera_id = camera_id

        frame_index = _frame_index(frame_index_by_name, image_name)
        poses.append(
            RawPose(
                frame_index=frame_index,
                frame_name=image_name,
                timestamp_sec=frame_index / frame_rate,
                position=_camera_center(qvec, tvec),
                rotation_xyzw=_camera_rotation_xyzw(qvec),
            )
        )
        line_index += 2

    if first_camera_id is None:
        raise ColmapPoseParseError("COLMAP output did not contain camera poses.")

    return sorted(poses, key=lambda pose: pose.frame_index), first_camera_id


def _data_lines(path: Path, missing_message: str) -> list[str]:
    try:
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except FileNotFoundError as error:
        raise ColmapPoseParseError(missing_message) from error


def _image_lines(images_path: Path) -> list[str]:
    try:
        return [
            line.rstrip()
            for line in images_path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        ]
    except FileNotFoundError as error:
        raise ColmapPoseParseError("COLMAP images.txt is missing.") from error


def _camera_intrinsics(model: str, width: int, height: int, params: list[float]) -> CameraIntrinsics:
    if model == "SIMPLE_PINHOLE" and len(params) >= 3:
        return CameraIntrinsics(width=width, height=height, fx=params[0], fy=params[0], cx=params[1], cy=params[2])

    if model == "PINHOLE" and len(params) >= 4:
        return CameraIntrinsics(width=width, height=height, fx=params[0], fy=params[1], cx=params[2], cy=params[3])

    raise ColmapPoseParseError(f"Unsupported COLMAP camera model: {model}")


def _frame_index_by_name(frames: list[Path]) -> dict[str, int]:
    return {frame.name: index for index, frame in enumerate(sorted(frames))}


def _frame_index(frame_index_by_name: dict[str, int], image_name: str) -> int:
    try:
        return frame_index_by_name[Path(image_name).name]
    except KeyError as error:
        raise ColmapPoseParseError(f"COLMAP image {image_name} does not match extracted frames.") from error


def _camera_rotation_xyzw(qvec: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    qw, qx, qy, qz = _normalized_qvec(qvec)
    return (-qx, -qy, -qz, qw)


def _camera_center(
    qvec: tuple[float, float, float, float],
    tvec: tuple[float, float, float],
) -> tuple[float, float, float]:
    qw, qx, qy, qz = _normalized_qvec(qvec)
    rotation = (
        (1 - 2 * qy * qy - 2 * qz * qz, 2 * qx * qy - 2 * qz * qw, 2 * qx * qz + 2 * qy * qw),
        (2 * qx * qy + 2 * qz * qw, 1 - 2 * qx * qx - 2 * qz * qz, 2 * qy * qz - 2 * qx * qw),
        (2 * qx * qz - 2 * qy * qw, 2 * qy * qz + 2 * qx * qw, 1 - 2 * qx * qx - 2 * qy * qy),
    )
    return tuple(-sum(rotation[row][column] * tvec[row] for row in range(3)) for column in range(3))


def _normalized_qvec(qvec: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    norm = sqrt(sum(value * value for value in qvec))
    if norm == 0:
        raise ColmapPoseParseError("COLMAP image quaternion must be non-zero.")

    return tuple(value / norm for value in qvec)


def _parse_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ColmapPoseParseError(f"COLMAP {label} is invalid.") from error


def _parse_float(value: str, label: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise ColmapPoseParseError(f"COLMAP {label} is invalid.") from error


class _ParsedCamera:
    def __init__(self, intrinsics: CameraIntrinsics) -> None:
        self.intrinsics = intrinsics
