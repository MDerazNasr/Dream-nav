from pathlib import Path

from remote_dense_app import colmap_command_adapter


def test_run_adapter_calls_colmap_dense_builder(tmp_path, monkeypatch) -> None:
    captured = {}
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    output_ply = tmp_path / "dense_result.ply"
    frames_root.mkdir(parents=True, exist_ok=True)

    def fake_builder(*, artifacts_root, frames_root, output_splat, camera_path=None, colmap_command=None):
        captured["artifacts_root"] = artifacts_root
        captured["frames_root"] = frames_root
        captured["output_splat"] = output_splat
        captured["camera_path"] = camera_path
        captured["colmap_command"] = colmap_command
        output_splat.write_text(
            "ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n0 0 0 255 255 255\n",
            encoding="utf-8",
        )
        return 1

    monkeypatch.setattr(colmap_command_adapter, "build_dense_splat_from_colmap", fake_builder)

    vertex_count = colmap_command_adapter.run_adapter(
        bundle_root=bundle_root,
        artifacts_root=artifacts_root,
        frames_root=frames_root,
        output_ply=output_ply,
        colmap_command="colmap",
    )

    assert vertex_count == 1
    assert captured["artifacts_root"] == artifacts_root
    assert captured["frames_root"] == frames_root
    assert captured["output_splat"] == output_ply
    assert captured["camera_path"] == artifacts_root / "camera_path.json"
    assert captured["colmap_command"] == "colmap"


def test_main_accepts_command_contract_arguments(tmp_path, monkeypatch) -> None:
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    output_ply = tmp_path / "dense_result.ply"
    frames_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(colmap_command_adapter, "run_adapter", lambda **kwargs: 5)

    status = colmap_command_adapter.main(
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


def test_health_check_requires_dense_capable_colmap(tmp_path, monkeypatch) -> None:
    colmap_path = tmp_path / "colmap"
    colmap_path.write_text(
        "#!/bin/sh\n"
        "echo 'COLMAP patch_match_stereo is unavailable without CUDA' >&2\n"
        "exit 0\n",
        encoding="utf-8",
    )
    colmap_path.chmod(0o755)
    monkeypatch.setattr(colmap_command_adapter, "which", lambda command: str(colmap_path))

    try:
        colmap_command_adapter.run_health_check()
    except colmap_command_adapter.RemoteDenseCommandAdapterError as error:
        assert "does not support dense stereo" in str(error)
    else:
        raise AssertionError("Expected dense-capability health check to fail")


def test_main_accepts_health_check_argument(monkeypatch) -> None:
    monkeypatch.setattr(colmap_command_adapter, "run_health_check", lambda colmap_command=None: 0)

    status = colmap_command_adapter.main(["--health-check"])

    assert status == 0
