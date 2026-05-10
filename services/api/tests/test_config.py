from app.config import default_settings


def test_default_settings_reads_pose_backend_env(monkeypatch) -> None:
    monkeypatch.setenv("DREAMNAV_POSE_BACKEND", "colmap")
    monkeypatch.setenv("DREAMNAV_POSE_COMMAND", "/opt/bin/colmap")
    monkeypatch.setenv("DREAMNAV_POSE_TIMEOUT_SEC", "12.5")
    monkeypatch.setenv("DREAMNAV_FRAME_BACKEND", "ffmpeg")
    monkeypatch.setenv("DREAMNAV_FRAME_COMMAND", "/opt/bin/ffmpeg")
    monkeypatch.setenv("DREAMNAV_FRAME_TIMEOUT_SEC", "8.5")
    monkeypatch.setenv("DREAMNAV_FRAME_RATE", "3")
    monkeypatch.setenv("DREAMNAV_FRAME_MAX_COUNT", "180")
    monkeypatch.setenv("DREAMNAV_FRAME_MAX_DURATION_SEC", "45")

    settings = default_settings()

    assert settings.processing.frame_backend == "ffmpeg"
    assert settings.processing.frame_command == "/opt/bin/ffmpeg"
    assert settings.processing.frame_timeout_sec == 8.5
    assert settings.processing.frame_rate == 3
    assert settings.processing.frame_max_count == 180
    assert settings.processing.frame_max_duration_sec == 45
    assert settings.processing.pose_backend == "colmap"
    assert settings.processing.pose_command == "/opt/bin/colmap"
    assert settings.processing.pose_timeout_sec == 12.5
