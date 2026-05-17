from pathlib import Path

from app.colmap_dense_to_splat import build_dense_splat_from_colmap
from app.point_cloud_bounds import filter_points_to_camera_bounds


def test_build_dense_splat_from_colmap_runs_dense_stereo_and_writes_splat(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    sparse_root = artifacts_root / "colmap" / "sparse" / "0"
    frames_root = artifacts_root / "frames"
    output_splat = artifacts_root / "splat.ply"
    sparse_root.mkdir(parents=True, exist_ok=True)
    frames_root.mkdir(parents=True, exist_ok=True)
    (frames_root / "frame_0000.jpg").write_bytes(b"jpg")
    (artifacts_root / "camera_path.json").write_text(
        '{"poses":[{"position":[0,1,-2]},{"position":[0.8,1.3,-2.6]}]}',
        encoding="utf-8",
    )
    (artifacts_root / "colmap" / "colmap_model_selection.json").write_text(
        '{"selected_model":"0"}',
        encoding="utf-8",
    )

    fake_colmap = tmp_path / "fake_colmap.py"
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        "command = sys.argv[1]\n"
        "if command == 'image_undistorter':\n"
        "    output = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "    output.mkdir(parents=True, exist_ok=True)\n"
        "if command == 'patch_match_stereo':\n"
        "    workspace = Path(sys.argv[sys.argv.index('--workspace_path') + 1])\n"
        "    workspace.mkdir(parents=True, exist_ok=True)\n"
        "if command == 'stereo_fusion':\n"
        "    output = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "    output.parent.mkdir(parents=True, exist_ok=True)\n"
        "    output.write_text(\n"
        "        'ply\\n'\n"
        "        'format ascii 1.0\\n'\n"
        "        'element vertex 3\\n'\n"
        "        'property float x\\n'\n"
        "        'property float y\\n'\n"
        "        'property float z\\n'\n"
        "        'property uchar red\\n'\n"
        "        'property uchar green\\n'\n"
        "        'property uchar blue\\n'\n"
        "        'end_header\\n'\n"
        "        '0 1 -2 255 0 0\\n'\n"
        "        '0.4 1.1 -2.2 0 255 64\\n'\n"
        "        '20 20 20 0 32 255\\n',\n"
        "        encoding='utf-8',\n"
        "    )\n"
        "print('fake colmap ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_colmap.chmod(0o755)

    vertex_count = build_dense_splat_from_colmap(
        artifacts_root,
        frames_root,
        output_splat,
        camera_path=artifacts_root / "camera_path.json",
        colmap_command=str(fake_colmap),
    )

    payload = output_splat.read_bytes()

    assert vertex_count == 2
    assert b"format binary_little_endian 1.0" in payload
    assert b"element vertex 2" in payload


def test_filter_points_to_camera_bounds_uses_supported_pose_cluster(tmp_path: Path) -> None:
    camera_path = tmp_path / "camera_path.json"
    camera_path.write_text(
        '{"poses":['
        '{"position":[-0.46,0.36,-0.12]},'
        '{"position":[-0.45,0.36,-0.12]},'
        '{"position":[-0.44,0.36,-0.12]},'
        '{"position":[-0.43,0.36,-0.12]},'
        '{"position":[-0.42,0.36,-0.12]},'
        '{"position":[-0.41,0.36,-0.12]},'
        '{"position":[-0.40,0.36,-0.12]},'
        '{"position":[-0.39,0.36,-0.12]},'
        '{"position":[7.2,-5.7,2.2]}'
        ']}',
        encoding="utf-8",
    )
    points = [
        {"position": [-0.42, 0.36, -0.12], "color": [255, 255, 255], "scale": 0.02},
        {"position": [7.15, -5.65, 2.18], "color": [255, 64, 0], "scale": 0.02},
    ]

    filtered = filter_points_to_camera_bounds(points, camera_path)

    assert len(filtered) == 1
    assert filtered[0]["position"] == [-0.42, 0.36, -0.12]
