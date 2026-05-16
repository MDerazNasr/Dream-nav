from pathlib import Path

from remote_dense_app import docker_command_adapter


def test_run_adapter_executes_containerized_dense_command(tmp_path, monkeypatch) -> None:
    captured = {}
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    output_ply = tmp_path / "out" / "dense_result.ply"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    frames_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(docker_command_adapter, "_resolve_runtime", lambda runtime: "/usr/local/bin/docker")
    monkeypatch.setattr(docker_command_adapter, "_resolve_image", lambda image: "dreamnav/dense-engine:latest")

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, capture_output, check, text):
        del capture_output, check, text
        captured["command"] = command
        output_ply.write_text(
            "ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n0 0 0 255 255 255\n",
            encoding="utf-8",
        )
        return Completed()

    monkeypatch.setattr(docker_command_adapter, "run", fake_run)

    docker_command_adapter.run_adapter(
        bundle_root=bundle_root,
        artifacts_root=artifacts_root,
        frames_root=frames_root,
        output_ply=output_ply,
    )

    assert captured["command"][0] == "/usr/local/bin/docker"
    assert "dreamnav/dense-engine:latest" in captured["command"]
    assert "--output-ply" in captured["command"]
    assert "/dreamnav/output/dense_result.ply" in captured["command"]


def test_main_accepts_optional_docker_overrides(tmp_path, monkeypatch) -> None:
    bundle_root = tmp_path / "bundle"
    artifacts_root = bundle_root / "artifacts"
    frames_root = bundle_root / "frames"
    output_ply = tmp_path / "dense_result.ply"
    frames_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(docker_command_adapter, "run_adapter", lambda **kwargs: None)

    status = docker_command_adapter.main(
        [
            "--bundle-root",
            str(bundle_root),
            "--artifacts-root",
            str(artifacts_root),
            "--frames-root",
            str(frames_root),
            "--output-ply",
            str(output_ply),
            "--docker-image",
            "dreamnav/dense-engine:latest",
        ]
    )

    assert status == 0


def test_resolve_image_requires_configuration(monkeypatch) -> None:
    monkeypatch.delenv("DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE", raising=False)

    try:
        docker_command_adapter._resolve_image(None)
    except docker_command_adapter.RemoteDenseDockerAdapterError as error:
        assert "DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE" in str(error)
    else:
        raise AssertionError("Expected docker image resolution to fail")


def test_probe_engine_reports_failed_image_health_check(monkeypatch) -> None:
    monkeypatch.setattr(docker_command_adapter, "_resolve_runtime", lambda runtime: "/usr/local/bin/docker")
    monkeypatch.setattr(docker_command_adapter, "_resolve_image", lambda image: "dreamnav/dense-engine:latest")

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "The dense engine image COLMAP build does not support dense stereo."

    monkeypatch.setattr(docker_command_adapter, "run", lambda *args, **kwargs: Completed())

    supported, reason = docker_command_adapter.probe_engine()

    assert supported is False
    assert reason == "The dense engine image COLMAP build does not support dense stereo."
