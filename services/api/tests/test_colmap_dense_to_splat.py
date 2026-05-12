from pathlib import Path

from app.colmap_dense_to_splat import build_dense_splat_from_colmap


def test_build_dense_splat_from_colmap_runs_dense_stereo_and_writes_splat(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    sparse_root = artifacts_root / "colmap" / "sparse" / "0"
    frames_root = artifacts_root / "frames"
    output_splat = artifacts_root / "splat.ply"
    sparse_root.mkdir(parents=True, exist_ok=True)
    frames_root.mkdir(parents=True, exist_ok=True)
    (frames_root / "frame_0000.jpg").write_bytes(b"jpg")
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
        "        '0.8 1.3 -2.6 0 32 255\\n',\n"
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
        colmap_command=str(fake_colmap),
    )

    payload = output_splat.read_bytes()

    assert vertex_count == 3
    assert b"format binary_little_endian 1.0" in payload
    assert b"element vertex 3" in payload

