from pathlib import Path

from remote_dense_app import trained_gaussian_backend


def test_run_backend_executes_train_command_and_writes_output(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    colmap_root = artifacts_root / "colmap"
    camera_path = artifacts_root / "camera_path.json"
    output_ply = tmp_path / "gaussian_result.ply"
    colmap_root.mkdir(parents=True, exist_ok=True)
    frames_root.mkdir(parents=True, exist_ok=True)
    camera_path.write_text("{}", encoding="utf-8")
    train_script = tmp_path / "train_backend.py"
    train_script.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from sys import argv\n"
        "parsed = dict(zip(argv[1::2], argv[2::2], strict=True))\n"
        "Path(parsed['--output-ply']).write_text(\n"
        "    'ply\\nformat ascii 1.0\\nelement vertex 1\\nproperty float x\\nproperty float y\\nproperty float z\\nproperty uchar red\\nproperty uchar green\\nproperty uchar blue\\nend_header\\n0 0 0 255 255 255\\n',\n"
        "    encoding='utf-8',\n"
        ")\n",
        encoding="utf-8",
    )
    train_script.chmod(0o755)

    trained_gaussian_backend.run_backend(
        bundle_root=bundle_root,
        artifacts_root=artifacts_root,
        frames_root=frames_root,
        camera_path=camera_path,
        colmap_root=colmap_root,
        output_ply=output_ply,
        train_command_json=f'["{train_script}","--output-ply","{{output_ply}}"]',
        export_command_json=None,
    )

    assert output_ply.is_file()


def test_probe_backend_accepts_json_command_array(tmp_path: Path) -> None:
    executable = tmp_path / "gaussian_backend.py"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)

    ready, reason = trained_gaussian_backend.probe_backend(
        train_command_json=f'["{executable}","--help"]',
        export_command_json=None,
    )

    assert ready is True
    assert reason is None


def test_main_accepts_health_check_argument(monkeypatch) -> None:
    monkeypatch.setattr(trained_gaussian_backend, "probe_backend", lambda **kwargs: (True, None))

    status = trained_gaussian_backend.main(["--health-check"])

    assert status == 0
