from app.config import default_settings


def test_default_settings_reads_pose_backend_env(monkeypatch) -> None:
    monkeypatch.setenv("DREAMNAV_POSE_BACKEND", "colmap")
    monkeypatch.setenv("DREAMNAV_POSE_COMMAND", "/opt/bin/colmap")
    monkeypatch.setenv("DREAMNAV_POSE_TIMEOUT_SEC", "12.5")

    settings = default_settings()

    assert settings.processing.pose_backend == "colmap"
    assert settings.processing.pose_command == "/opt/bin/colmap"
    assert settings.processing.pose_timeout_sec == 12.5
