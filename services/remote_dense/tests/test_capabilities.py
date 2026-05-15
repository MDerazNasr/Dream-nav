from pathlib import Path

from fastapi.testclient import TestClient

from remote_dense_app.main import RemoteDenseSettings, create_app


def test_capabilities_reports_real_dense_ready_when_external_adapter_exists(tmp_path, monkeypatch) -> None:
    adapter_path = tmp_path / "colmap_command_adapter.py"
    adapter_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    adapter_path.chmod(0o755)
    monkeypatch.setattr(
        "remote_dense_app.capabilities.detect_colmap_dense_support",
        lambda command: (False, "The configured COLMAP build does not support dense stereo."),
    )

    app = create_app(
        RemoteDenseSettings(
            repo_root=tmp_path,
            backend="auto",
            dense_command=str(adapter_path),
            allow_mock_fallback=True,
            retained_job_count=4,
        )
    )
    client = TestClient(app)

    response = client.get("/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["bundled_adapter_available"] is True
    assert payload["real_dense_ready"] is True
    assert payload["colmap_dense_supported"] is False
    assert payload["warnings"] == ["The configured COLMAP build does not support dense stereo."]


def test_capabilities_block_bundled_adapter_when_colmap_dense_is_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "remote_dense_app.capabilities.detect_colmap_dense_support",
        lambda command: (False, "The configured COLMAP build does not support dense stereo."),
    )
    app = create_app(
        RemoteDenseSettings(
            repo_root=tmp_path,
            backend="auto",
            dense_command=str(Path(__file__).resolve().parents[1] / "remote_dense_app" / "colmap_command_adapter.py"),
            allow_mock_fallback=True,
        )
    )
    client = TestClient(app)

    response = client.get("/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["bundled_adapter_available"] is True
    assert payload["real_dense_ready"] is False
    assert "Run the worker on a machine that can execute a real dense reconstruction backend." in payload["missing_requirements"]


def test_capabilities_reports_missing_requirements_when_no_real_backend_is_available(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "remote_dense_app.capabilities.detect_colmap_dense_support",
        lambda command: (False, "The configured COLMAP build does not support dense stereo."),
    )
    app = create_app(
        RemoteDenseSettings(
            repo_root=tmp_path,
            backend="command",
            dense_command=str(tmp_path / "missing_adapter.py"),
            allow_mock_fallback=False,
        )
    )
    client = TestClient(app)

    response = client.get("/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["bundled_adapter_available"] is False
    assert payload["real_dense_ready"] is False
    assert "Set DREAMNAV_REMOTE_DENSE_COMMAND to a valid executable." in payload["missing_requirements"]
