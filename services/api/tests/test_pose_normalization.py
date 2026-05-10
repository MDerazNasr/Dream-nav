from pathlib import Path

import pytest

from app.pose_normalization import (
    CameraIntrinsics,
    PoseNormalizationError,
    RawPose,
    normalize_camera_path,
    stub_raw_poses_from_frames,
)


def test_normalize_camera_path_exports_viewer_contract() -> None:
    camera_path = normalize_camera_path(
        "scene_abc123",
        [
            RawPose(
                frame_index=0,
                frame_name="frame_0000.jpg",
                timestamp_sec=0,
                position=(0, 1.5, 0),
                rotation_xyzw=(0, 0, 0, 1),
            )
        ],
    )

    assert camera_path["scene_id"] == "scene_abc123"
    assert camera_path["coordinate_system"] == "dreamnav_viewer_v1"
    assert camera_path["poses"][0]["frame_index"] == 0
    assert camera_path["poses"][0]["rotation_xyzw"] == [0, 0, 0, 1]


def test_stub_raw_poses_map_frames_to_timestamps() -> None:
    poses = stub_raw_poses_from_frames(
        [Path("frame_0000.jpg"), Path("frame_0001.jpg"), Path("frame_0002.jpg")],
        frame_rate=2,
    )

    assert [pose.frame_name for pose in poses] == [
        "frame_0000.jpg",
        "frame_0001.jpg",
        "frame_0002.jpg",
    ]
    assert [pose.timestamp_sec for pose in poses] == [0, 0.5, 1]


def test_stub_raw_poses_require_extracted_frames() -> None:
    with pytest.raises(PoseNormalizationError, match="requires extracted frames"):
        stub_raw_poses_from_frames([], frame_rate=2)


def test_normalize_camera_path_rejects_invalid_pose_values() -> None:
    with pytest.raises(PoseNormalizationError, match="finite"):
        normalize_camera_path(
            "scene_abc123",
            [
                RawPose(
                    frame_index=0,
                    frame_name="frame_0000.jpg",
                    timestamp_sec=0,
                    position=(0, float("nan"), 0),
                    rotation_xyzw=(0, 0, 0, 1),
                )
            ],
        )


def test_normalize_camera_path_rejects_invalid_intrinsics() -> None:
    with pytest.raises(PoseNormalizationError, match="dimensions"):
        normalize_camera_path(
            "scene_abc123",
            [
                RawPose(
                    frame_index=0,
                    frame_name="frame_0000.jpg",
                    timestamp_sec=0,
                    position=(0, 1.5, 0),
                    rotation_xyzw=(0, 0, 0, 1),
                )
            ],
            intrinsics=CameraIntrinsics(width=0, height=1080, fx=1240, fy=1240, cx=960, cy=540),
        )
