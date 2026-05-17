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
    executable = tmp_path / "fake_gaussian.py"
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
