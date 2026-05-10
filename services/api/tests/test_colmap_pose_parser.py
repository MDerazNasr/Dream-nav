from pathlib import Path

import pytest

from app.colmap_pose_parser import ColmapPoseParseError, parse_colmap_text_model


def test_parse_colmap_text_model_maps_images_to_frames(tmp_path: Path) -> None:
    model_root = _write_model(
        tmp_path,
        cameras="1 PINHOLE 1920 1080 1200 1210 960 540\n",
        images=(
            "1 1 0 0 0 0 0 0 1 frame_0000.jpg\n"
            "\n"
            "2 1 0 0 0 -1 -2 -3 1 frame_0001.jpg\n"
            "\n"
        ),
    )

    poses, intrinsics = parse_colmap_text_model(
        model_root,
        [Path("frame_0000.jpg"), Path("frame_0001.jpg")],
        frame_rate=2,
    )

    assert intrinsics.fx == 1200
    assert intrinsics.fy == 1210
    assert [pose.frame_index for pose in poses] == [0, 1]
    assert poses[1].timestamp_sec == 0.5
    assert poses[1].position == (1, 2, 3)
    assert poses[1].rotation_xyzw == (0, 0, 0, 1)


def test_parse_colmap_text_model_supports_simple_pinhole(tmp_path: Path) -> None:
    model_root = _write_model(
        tmp_path,
        cameras="1 SIMPLE_PINHOLE 1920 1080 1240 960 540\n",
        images="1 1 0 0 0 0 0 0 1 frame_0000.jpg\n\n",
    )

    _poses, intrinsics = parse_colmap_text_model(model_root, [Path("frame_0000.jpg")], frame_rate=2)

    assert intrinsics.fx == 1240
    assert intrinsics.fy == 1240


def test_parse_colmap_text_model_rejects_missing_outputs(tmp_path: Path) -> None:
    with pytest.raises(ColmapPoseParseError, match="cameras.txt is missing"):
        parse_colmap_text_model(tmp_path / "missing", [Path("frame_0000.jpg")], frame_rate=2)


def test_parse_colmap_text_model_rejects_unknown_frame_names(tmp_path: Path) -> None:
    model_root = _write_model(
        tmp_path,
        cameras="1 PINHOLE 1920 1080 1200 1210 960 540\n",
        images="1 1 0 0 0 0 0 0 1 other.jpg\n\n",
    )

    with pytest.raises(ColmapPoseParseError, match="does not match extracted frames"):
        parse_colmap_text_model(model_root, [Path("frame_0000.jpg")], frame_rate=2)


def test_parse_colmap_text_model_rejects_pose_count_mismatch(tmp_path: Path) -> None:
    model_root = _write_model(
        tmp_path,
        cameras="1 PINHOLE 1920 1080 1200 1210 960 540\n",
        images="1 1 0 0 0 0 0 0 1 frame_0000.jpg\n\n",
    )

    with pytest.raises(ColmapPoseParseError, match="does not match extracted frame count"):
        parse_colmap_text_model(
            model_root,
            [Path("frame_0000.jpg"), Path("frame_0001.jpg")],
            frame_rate=2,
        )


def test_parse_colmap_text_model_rejects_malformed_pose_rows(tmp_path: Path) -> None:
    model_root = _write_model(
        tmp_path,
        cameras="1 PINHOLE 1920 1080 1200 1210 960 540\n",
        images="1 1 0 0 0 0 0 0\n\n",
    )

    with pytest.raises(ColmapPoseParseError, match="malformed image row"):
        parse_colmap_text_model(model_root, [Path("frame_0000.jpg")], frame_rate=2)


def _write_model(tmp_path: Path, cameras: str, images: str) -> Path:
    model_root = tmp_path / "colmap"
    model_root.mkdir()
    (model_root / "cameras.txt").write_text(cameras, encoding="utf-8")
    (model_root / "images.txt").write_text(images, encoding="utf-8")
    return model_root
