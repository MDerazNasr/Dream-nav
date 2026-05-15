from pathlib import Path

import pytest

from remote_dense_app import backend
from remote_dense_app.backend import DenseBuildResult, RemoteDenseBackendError, build_dense_result
from test_helpers import build_bundle_bytes


def test_build_dense_result_auto_falls_back_to_mock_without_dense_support(tmp_path, monkeypatch) -> None:
    bundle_path = tmp_path / "bundle.zip"
    bundle_path.write_bytes(build_bundle_bytes(include_colmap_sparse=True))

    monkeypatch.setattr(
        backend,
        "detect_colmap_dense_support",
        lambda command: (False, "The configured COLMAP build does not support dense stereo."),
    )

    result = build_dense_result(bundle_path, tmp_path / "workspace", "auto", None, None, allow_mock_fallback=True)

    assert result.backend == "mock"
    assert result.dense_ply.startswith(b"ply\nformat ascii 1.0\n")
    assert result.warnings == [
        "colmap_dense: The configured COLMAP build does not support dense stereo.",
    ]


def test_build_dense_result_uses_colmap_dense_when_supported(tmp_path, monkeypatch) -> None:
    bundle_path = tmp_path / "bundle.zip"
    bundle_path.write_bytes(build_bundle_bytes(include_colmap_sparse=True))

    monkeypatch.setattr(backend, "detect_colmap_dense_support", lambda command: (True, None))
    monkeypatch.setattr(
        backend,
        "build_dense_colmap_ply",
        lambda extracted_root, workspace_root, command: b"ply\nformat ascii 1.0\nmock dense\n",
    )

    result = build_dense_result(bundle_path, tmp_path / "workspace", "auto", "colmap", None, allow_mock_fallback=True)

    assert result == DenseBuildResult(
        backend="colmap_dense",
        dense_ply=b"ply\nformat ascii 1.0\nmock dense\n",
        warnings=[],
    )


def test_build_dense_result_rejects_missing_sparse_model_when_real_backend_is_forced(tmp_path) -> None:
    bundle_path = tmp_path / "bundle.zip"
    bundle_path.write_bytes(build_bundle_bytes(include_colmap_sparse=False))

    with pytest.raises(RemoteDenseBackendError, match="did not include COLMAP sparse artifacts"):
        build_dense_result(bundle_path, tmp_path / "workspace", "colmap_dense", None, None, allow_mock_fallback=True)


def test_build_dense_result_uses_command_backend_when_configured(tmp_path) -> None:
    bundle_path = tmp_path / "bundle.zip"
    bundle_path.write_bytes(build_bundle_bytes(include_colmap_sparse=True))
    command_path = tmp_path / "fake_dense_command.py"
    command_path.write_text(
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
    command_path.chmod(0o755)

    result = build_dense_result(
        bundle_path,
        tmp_path / "workspace",
        "command",
        None,
        str(command_path),
        allow_mock_fallback=True,
    )

    assert result.backend == "command"
    assert result.warnings == []
    assert b"property float f_dc_0" in result.dense_ply
    assert b"property float opacity" in result.dense_ply


def test_build_dense_result_passes_through_splat_output_from_command_backend(tmp_path) -> None:
    bundle_path = tmp_path / "bundle.zip"
    bundle_path.write_bytes(build_bundle_bytes(include_colmap_sparse=True))
    command_path = tmp_path / "fake_dense_command.py"
    command_path.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from sys import argv\n"
        "parsed = dict(zip(argv[1::2], argv[2::2], strict=True))\n"
        "Path(parsed['--output-ply']).write_text(\n"
        "    'ply\\nformat binary_little_endian 1.0\\nelement vertex 1\\nproperty float x\\nproperty float y\\nproperty float z\\nproperty float f_dc_0\\nproperty float f_dc_1\\nproperty float f_dc_2\\nproperty float opacity\\nproperty float scale_0\\nproperty float scale_1\\nproperty float scale_2\\nproperty float rot_0\\nproperty float rot_1\\nproperty float rot_2\\nproperty float rot_3\\nend_header\\n',\n"
        "    encoding='utf-8',\n"
        ")\n",
        encoding="utf-8",
    )
    command_path.chmod(0o755)

    result = build_dense_result(
        bundle_path,
        tmp_path / "workspace",
        "command",
        None,
        str(command_path),
        allow_mock_fallback=True,
    )

    assert result.backend == "command"
    assert b"property float f_dc_0" in result.dense_ply
    assert b"property float opacity" in result.dense_ply


def test_detect_colmap_dense_support_rejects_cuda_less_build(tmp_path) -> None:
    colmap_path = tmp_path / "colmap"
    colmap_path.write_text(
        "#!/bin/sh\n"
        "echo 'COLMAP patch_match_stereo is unavailable without CUDA' >&2\n"
        "exit 0\n",
        encoding="utf-8",
    )
    colmap_path.chmod(0o755)

    supported, reason = backend.detect_colmap_dense_support(str(colmap_path))

    assert supported is False
    assert reason == "The configured COLMAP build does not support dense stereo."
