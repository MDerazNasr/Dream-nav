import json
from pathlib import Path

from remote_dense_app import nerfstudio_splatfacto_backend


def test_run_backend_materializes_dataset_and_exports_ply(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    colmap_root = artifacts_root / "colmap"
    output_ply = tmp_path / "gaussian_result.ply"
    frames_root.mkdir(parents=True, exist_ok=True)
    colmap_root.mkdir(parents=True, exist_ok=True)

    (frames_root / "frame_0001.jpg").write_bytes(b"jpg1")
    (frames_root / "frame_0002.jpg").write_bytes(b"jpg2")
    (artifacts_root / "camera_path.json").write_text(
        json.dumps(
            {
                "intrinsics": {
                    "width": 1280,
                    "height": 720,
                    "fx": 800,
                    "fy": 810,
                    "cx": 640,
                    "cy": 360,
                },
                "poses": [
                    {
                        "frame_index": 0,
                        "position": [0.0, 0.0, 0.0],
                        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    },
                    {
                        "frame_index": 1,
                        "position": [1.0, 0.0, 0.0],
                        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (colmap_root / "points3D.txt").write_text(
        "1 0.0 1.0 2.0 255 0 0 0.5 1 1 2\n"
        "2 1.0 2.0 3.0 0 255 0 0.5 1 1 2\n",
        encoding="utf-8",
    )

    train_script = tmp_path / "fake_ns_train.py"
    train_script.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from sys import argv\n"
        "if len(argv) > 2 and argv[1] == 'splatfacto' and argv[2] == '--help':\n"
        "    raise SystemExit(0)\n"
        "assert 'colmap' not in argv\n"
        "assert '--vis' in argv\n"
        "assert argv[argv.index('--vis') + 1] == 'tensorboard'\n"
        "data_root = Path(argv[argv.index('--data') + 1])\n"
        "workspace_root = Path.cwd()\n"
        "(workspace_root / 'outputs' / 'run').mkdir(parents=True, exist_ok=True)\n"
        "(workspace_root / 'outputs' / 'run' / 'config.yml').write_text('trainer: ok\\n', encoding='utf-8')\n"
        "payload = __import__('json').loads((data_root / 'transforms.json').read_text(encoding='utf-8'))\n"
        "assert payload['frames'][0]['file_path'] == 'images/frame_0001.jpg'\n"
        "assert payload['frames'][1]['file_path'] == 'images/frame_0002.jpg'\n"
        "assert payload['ply_file_path'] == 'sparse_pc.ply'\n",
        encoding="utf-8",
    )
    train_script.chmod(0o755)

    export_script = tmp_path / "fake_ns_export.py"
    export_script.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from sys import argv\n"
        "if len(argv) > 2 and argv[1] == 'gaussian-splat' and argv[2] == '--help':\n"
        "    raise SystemExit(0)\n"
        "output_dir = Path(argv[argv.index('--output-dir') + 1])\n"
        "output_dir.mkdir(parents=True, exist_ok=True)\n"
        "(output_dir / 'splat.ply').write_text(\n"
        "    'ply\\nformat ascii 1.0\\nelement vertex 1\\nproperty float x\\nproperty float y\\nproperty float z\\nproperty uchar red\\nproperty uchar green\\nproperty uchar blue\\nend_header\\n0 0 0 255 255 255\\n',\n"
        "    encoding='utf-8',\n"
        ")\n",
        encoding="utf-8",
    )
    export_script.chmod(0o755)

    nerfstudio_splatfacto_backend.run_backend(
        bundle_root=bundle_root,
        artifacts_root=artifacts_root,
        frames_root=frames_root,
        camera_path=artifacts_root / "camera_path.json",
        colmap_root=colmap_root,
        output_ply=output_ply,
        train_command=str(train_script),
        export_command=str(export_script),
    )

    assert output_ply.is_file()
    transforms = json.loads(
        (output_ply.parent / "nerfstudio-splatfacto-workspace" / "dataset" / "transforms.json").read_text(encoding="utf-8")
    )
    assert transforms["frames"][0]["file_path"] == "images/frame_0001.jpg"
    assert transforms["frames"][1]["file_path"] == "images/frame_0002.jpg"
    assert transforms["ply_file_path"] == "sparse_pc.ply"
    assert transforms["applied_transform"] == [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [-0.0, -1.0, -0.0, -0.0],
    ]
    assert transforms["frames"][0]["transform_matrix"] == [
        [1.0, -0.0, -0.0, 0.0],
        [0.0, -1.0, -0.0, 0.0],
        [0.0, -0.0, -1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    assert (
        output_ply.parent / "nerfstudio-splatfacto-workspace" / "dataset" / "sparse_pc.ply"
    ).is_file()


def test_run_backend_prefers_raw_colmap_dataset_when_available(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    colmap_root = artifacts_root / "colmap"
    output_ply = tmp_path / "gaussian_result.ply"
    frames_root.mkdir(parents=True, exist_ok=True)
    colmap_root.mkdir(parents=True, exist_ok=True)

    (frames_root / "frame_0001.jpg").write_bytes(b"jpg1")
    (frames_root / "frame_0002.jpg").write_bytes(b"jpg2")
    (artifacts_root / "camera_path.json").write_text(
        json.dumps(
            {
                "intrinsics": {"width": 1280, "height": 720, "fx": 800, "fy": 810, "cx": 640, "cy": 360},
                "poses": [{"frame_index": 0, "position": [9.0, 9.0, 9.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}],
            }
        ),
        encoding="utf-8",
    )
    (colmap_root / "cameras.txt").write_text(
        "# header\n"
        "1 SIMPLE_RADIAL 1280 720 700.0 640.0 360.0 0.12\n"
        "2 SIMPLE_RADIAL 1280 720 710.0 640.0 360.0 0.08\n",
        encoding="utf-8",
    )
    (colmap_root / "images.txt").write_text(
        "# header\n"
        "1 1 0 0 0 0 0 0 1 frame_0001.jpg\n"
        "0 0 -1\n"
        "2 1 0 0 0 -1 0 0 2 frame_0002.jpg\n"
        "0 0 -1\n",
        encoding="utf-8",
    )
    (colmap_root / "points3D.txt").write_text(
        "1 0.0 1.0 2.0 255 0 0 0.5 1 1 2\n",
        encoding="utf-8",
    )

    train_script = tmp_path / "fake_ns_train.py"
    train_script.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from sys import argv\n"
        "if len(argv) > 2 and argv[1] == 'splatfacto' and argv[2] == '--help':\n"
        "    raise SystemExit(0)\n"
        "assert 'colmap' in argv\n"
        "assert argv[argv.index('--pipeline.model.enable-collider') + 1] == 'False'\n"
        "assert argv[argv.index('colmap') + 1: argv.index('colmap') + 15] == [\n"
        "    '--orientation-method', 'none',\n"
        "    '--center-method', 'none',\n"
        "    '--auto-scale-poses', 'False',\n"
        "    '--assume-colmap-world-coordinate-convention', 'False',\n"
        "    '--eval-mode', 'all',\n"
        "    '--downscale-factor', '1',\n"
        "    '--images-path', 'images',\n"
        "]\n"
        "assert argv[argv.index('--colmap-path') + 1] == 'colmap/sparse/0'\n"
        "assert argv.index('--pipeline.model.enable-collider') < argv.index('colmap')\n"
        "data_root = Path(argv[argv.index('--data') + 1])\n"
        "assert (data_root / 'colmap' / 'sparse' / '0' / 'cameras.txt').is_file()\n"
        "assert (data_root / 'colmap' / 'sparse' / '0' / 'images.txt').is_file()\n"
        "assert (data_root / 'colmap' / 'sparse' / '0' / 'points3D.txt').is_file()\n"
        "workspace_root = Path.cwd()\n"
        "(workspace_root / 'outputs' / 'run').mkdir(parents=True, exist_ok=True)\n"
        "(workspace_root / 'outputs' / 'run' / 'config.yml').write_text('trainer: ok\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    train_script.chmod(0o755)

    export_script = tmp_path / "fake_ns_export.py"
    export_script.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from sys import argv\n"
        "if len(argv) > 2 and argv[1] == 'gaussian-splat' and argv[2] == '--help':\n"
        "    raise SystemExit(0)\n"
        "output_dir = Path(argv[argv.index('--output-dir') + 1])\n"
        "output_dir.mkdir(parents=True, exist_ok=True)\n"
        "(output_dir / 'splat.ply').write_text(\n"
        "    'ply\\nformat ascii 1.0\\nelement vertex 1\\nproperty float x\\nproperty float y\\nproperty float z\\nproperty uchar red\\nproperty uchar green\\nproperty uchar blue\\nend_header\\n0 0 0 255 255 255\\n',\n"
        "    encoding='utf-8',\n"
        ")\n",
        encoding="utf-8",
    )
    export_script.chmod(0o755)

    nerfstudio_splatfacto_backend.run_backend(
        bundle_root=bundle_root,
        artifacts_root=artifacts_root,
        frames_root=frames_root,
        camera_path=artifacts_root / "camera_path.json",
        colmap_root=colmap_root,
        output_ply=output_ply,
        train_command=str(train_script),
        export_command=str(export_script),
    )

    dataset_root = output_ply.parent / "nerfstudio-splatfacto-workspace" / "dataset"
    assert not (dataset_root / "transforms.json").exists()
    assert (dataset_root / "images" / "frame_0001.jpg").exists()
    assert (dataset_root / "colmap" / "sparse" / "0" / "cameras.txt").is_file()
    assert (dataset_root / "colmap" / "sparse" / "0" / "images.txt").is_file()
    assert (dataset_root / "colmap" / "sparse" / "0" / "points3D.txt").is_file()


def test_run_backend_allows_enabling_official_colmap_collider(tmp_path: Path, monkeypatch) -> None:
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    colmap_root = artifacts_root / "colmap"
    output_ply = tmp_path / "gaussian_result.ply"
    frames_root.mkdir(parents=True, exist_ok=True)
    colmap_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DREAMNAV_NERFSTUDIO_ENABLE_COLLIDER", "true")

    (frames_root / "frame_0001.jpg").write_bytes(b"jpg1")
    (artifacts_root / "camera_path.json").write_text(
        json.dumps(
            {
                "intrinsics": {"width": 1280, "height": 720, "fx": 800, "fy": 810, "cx": 640, "cy": 360},
                "poses": [{"frame_index": 0, "position": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}],
            }
        ),
        encoding="utf-8",
    )
    (colmap_root / "cameras.txt").write_text(
        "1 SIMPLE_RADIAL 1280 720 700.0 640.0 360.0 0.12\n",
        encoding="utf-8",
    )
    (colmap_root / "images.txt").write_text(
        "1 1 0 0 0 0 0 0 1 frame_0001.jpg\n0 0 -1\n",
        encoding="utf-8",
    )
    (colmap_root / "points3D.txt").write_text(
        "1 0.0 1.0 2.0 255 0 0 0.5 1 1 2\n",
        encoding="utf-8",
    )

    train_script = tmp_path / "fake_ns_train.py"
    train_script.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from sys import argv\n"
        "assert '--pipeline.model.enable-collider' not in argv\n"
        "workspace_root = Path.cwd()\n"
        "(workspace_root / 'outputs' / 'run').mkdir(parents=True, exist_ok=True)\n"
        "(workspace_root / 'outputs' / 'run' / 'config.yml').write_text('trainer: ok\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    train_script.chmod(0o755)

    export_script = tmp_path / "fake_ns_export.py"
    export_script.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from sys import argv\n"
        "output_dir = Path(argv[argv.index('--output-dir') + 1])\n"
        "output_dir.mkdir(parents=True, exist_ok=True)\n"
        "(output_dir / 'splat.ply').write_text(\n"
        "    'ply\\nformat ascii 1.0\\nelement vertex 1\\nproperty float x\\nproperty float y\\nproperty float z\\nproperty uchar red\\nproperty uchar green\\nproperty uchar blue\\nend_header\\n0 0 0 255 255 255\\n',\n"
        "    encoding='utf-8',\n"
        ")\n",
        encoding="utf-8",
    )
    export_script.chmod(0o755)

    nerfstudio_splatfacto_backend.run_backend(
        bundle_root=bundle_root,
        artifacts_root=artifacts_root,
        frames_root=frames_root,
        camera_path=artifacts_root / "camera_path.json",
        colmap_root=colmap_root,
        output_ply=output_ply,
        train_command=str(train_script),
        export_command=str(export_script),
    )

    assert output_ply.is_file()


def test_probe_backend_checks_splatfacto_and_gaussian_export_help(tmp_path: Path) -> None:
    train_executable = tmp_path / "ns-train"
    train_executable.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"splatfacto\" ] && [ \"$2\" = \"--help\" ]; then exit 0; fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    train_executable.chmod(0o755)
    export_executable = tmp_path / "ns-export"
    export_executable.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"gaussian-splat\" ] && [ \"$2\" = \"--help\" ]; then exit 0; fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    export_executable.chmod(0o755)

    ready, reason = nerfstudio_splatfacto_backend.probe_backend(
        train_command=str(train_executable),
        export_command=str(export_executable),
    )

    assert ready is True
    assert reason is None
