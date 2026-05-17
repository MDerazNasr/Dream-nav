from pathlib import Path

from remote_dense_app import gaussian_command_adapter


def test_run_adapter_calls_external_gaussian_executable(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    output_ply = tmp_path / "gaussian_result.ply"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    frames_root.mkdir(parents=True, exist_ok=True)
    executable = tmp_path / "fake_gaussian.py"
    executable.write_text(
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
    executable.chmod(0o755)

    gaussian_command_adapter.run_adapter(
        bundle_root=bundle_root,
        artifacts_root=artifacts_root,
        frames_root=frames_root,
        output_ply=output_ply,
        gaussian_executable=str(executable),
    )

    assert output_ply.is_file()


def test_probe_engine_accepts_health_check_or_help(tmp_path: Path) -> None:
    executable = tmp_path / "fake_gaussian"
    executable.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--health-check\" ]; then exit 1; fi\n"
        "if [ \"$1\" = \"--help\" ]; then exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)

    ready, reason = gaussian_command_adapter.probe_engine(str(executable))

    assert ready is True
    assert reason is None


def test_probe_engine_defaults_to_bundled_backend_when_training_commands_are_configured(tmp_path, monkeypatch) -> None:
    backend_path = Path(gaussian_command_adapter.__file__).with_name("trained_gaussian_backend.py")
    monkeypatch.setenv("DREAMNAV_TRAINED_GAUSSIAN_TRAIN_COMMAND_JSON", '["echo","ok"]')
    monkeypatch.delenv("DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE", raising=False)

    ready, reason = gaussian_command_adapter.probe_engine()

    assert ready is True
    assert reason is None
    assert backend_path.is_file()


def test_probe_engine_prefers_nerfstudio_backend_when_configured(monkeypatch) -> None:
    backend_path = Path(gaussian_command_adapter.__file__).with_name("nerfstudio_splatfacto_backend.py")
    monkeypatch.setenv("DREAMNAV_NERFSTUDIO_TRAIN_COMMAND", "missing-train")
    monkeypatch.delenv("DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE", raising=False)
    monkeypatch.delenv("DREAMNAV_TRAINED_GAUSSIAN_TRAIN_COMMAND_JSON", raising=False)
    monkeypatch.delenv("DREAMNAV_TRAINED_GAUSSIAN_EXPORT_COMMAND_JSON", raising=False)

    ready, reason = gaussian_command_adapter.probe_engine()

    assert ready is False
    assert "Nerfstudio train command was not found." in (reason or "")
    assert backend_path.is_file()


def test_main_accepts_command_contract_arguments(tmp_path, monkeypatch) -> None:
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    output_ply = tmp_path / "gaussian_result.ply"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    frames_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(gaussian_command_adapter, "run_adapter", lambda **kwargs: None)

    status = gaussian_command_adapter.main(
        [
            "--bundle-root",
            str(bundle_root),
            "--artifacts-root",
            str(artifacts_root),
            "--frames-root",
            str(frames_root),
            "--output-ply",
            str(output_ply),
        ]
    )

    assert status == 0
