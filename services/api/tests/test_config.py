import app.config as config_module
from app.config import default_settings


def test_default_settings_reads_pose_backend_env(monkeypatch) -> None:
    monkeypatch.setenv("DREAMNAV_POSE_BACKEND", "colmap")
    monkeypatch.setenv("DREAMNAV_POSE_COMMAND", "/opt/bin/colmap")
    monkeypatch.setenv("DREAMNAV_POSE_TIMEOUT_SEC", "12.5")
    monkeypatch.setenv("DREAMNAV_GAUSSIAN_BACKEND", "command")
    monkeypatch.setenv("DREAMNAV_GAUSSIAN_COMMAND", "/opt/bin/reconstruct")
    monkeypatch.setenv("DREAMNAV_GAUSSIAN_TIMEOUT_SEC", "90")
    monkeypatch.setenv("DREAMNAV_FRAME_BACKEND", "ffmpeg")
    monkeypatch.setenv("DREAMNAV_FRAME_COMMAND", "/opt/bin/ffmpeg")
    monkeypatch.setenv("DREAMNAV_FRAME_TIMEOUT_SEC", "8.5")
    monkeypatch.setenv("DREAMNAV_FRAME_RATE", "3")
    monkeypatch.setenv("DREAMNAV_FRAME_MAX_COUNT", "180")
    monkeypatch.setenv("DREAMNAV_FRAME_MAX_DURATION_SEC", "45")
    monkeypatch.setenv("DREAMNAV_PUBLIC_API_BASE_URL", "https://dreamnav.example")
    monkeypatch.setenv("DREAMNAV_REMOTE_DENSE_URL", "https://dense.example/jobs")
    monkeypatch.setenv("DREAMNAV_REMOTE_DENSE_TOKEN", "provider-secret")
    monkeypatch.setenv("DREAMNAV_REMOTE_DENSE_CALLBACK_TOKEN", "callback-secret")

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
    assert settings.processing.gaussian_backend == "command"
    assert settings.processing.gaussian_command == "/opt/bin/reconstruct"
    assert settings.processing.gaussian_timeout_sec == 90
    assert settings.public_api_base_url == "https://dreamnav.example"
    assert settings.remote_dense_url == "https://dense.example/jobs"
    assert settings.remote_dense_token == "provider-secret"
    assert settings.remote_dense_callback_token == "callback-secret"


def test_default_settings_prefers_ffmpeg_when_available(monkeypatch) -> None:
    monkeypatch.delenv("DREAMNAV_FRAME_BACKEND", raising=False)
    monkeypatch.delenv("DREAMNAV_FRAME_COMMAND", raising=False)
    monkeypatch.delenv("DREAMNAV_POSE_BACKEND", raising=False)
    monkeypatch.delenv("DREAMNAV_POSE_COMMAND", raising=False)
    monkeypatch.setattr(config_module, "which", lambda command: "/opt/homebrew/bin/ffmpeg" if command == "ffmpeg" else None)

    settings = default_settings()

    assert settings.processing.frame_backend == "ffmpeg"
    assert settings.processing.frame_command == "/opt/homebrew/bin/ffmpeg"


def test_default_settings_prefers_colmap_when_available(monkeypatch) -> None:
    monkeypatch.delenv("DREAMNAV_FRAME_BACKEND", raising=False)
    monkeypatch.delenv("DREAMNAV_FRAME_COMMAND", raising=False)
    monkeypatch.delenv("DREAMNAV_POSE_BACKEND", raising=False)
    monkeypatch.delenv("DREAMNAV_POSE_COMMAND", raising=False)
    monkeypatch.setattr(
        config_module,
        "which",
        lambda command: "/opt/homebrew/bin/colmap" if command == "colmap" else None,
    )

    settings = default_settings()

    assert settings.processing.pose_backend == "colmap"
    assert settings.processing.pose_command == "/opt/homebrew/bin/colmap"


def test_default_settings_prefers_internal_gaussian_wrapper_when_colmap_is_available(monkeypatch) -> None:
    monkeypatch.delenv("DREAMNAV_FRAME_BACKEND", raising=False)
    monkeypatch.delenv("DREAMNAV_FRAME_COMMAND", raising=False)
    monkeypatch.delenv("DREAMNAV_POSE_BACKEND", raising=False)
    monkeypatch.delenv("DREAMNAV_POSE_COMMAND", raising=False)
    monkeypatch.delenv("DREAMNAV_GAUSSIAN_BACKEND", raising=False)
    monkeypatch.delenv("DREAMNAV_GAUSSIAN_COMMAND", raising=False)
    monkeypatch.setattr(
        config_module,
        "which",
        lambda command: "/opt/homebrew/bin/colmap" if command == "colmap" else None,
    )

    settings = default_settings()

    assert settings.processing.gaussian_backend == "command"
    assert settings.processing.gaussian_command is not None
    assert settings.processing.gaussian_command.endswith("colmap_sparse_to_splat.py")


def test_default_settings_uses_real_pose_timeout_budget(monkeypatch) -> None:
    monkeypatch.delenv("DREAMNAV_POSE_TIMEOUT_SEC", raising=False)

    settings = default_settings()

    assert settings.processing.pose_timeout_sec == 180


def test_default_settings_use_denser_live_frame_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DREAMNAV_FRAME_TIMEOUT_SEC", raising=False)
    monkeypatch.delenv("DREAMNAV_FRAME_RATE", raising=False)
    monkeypatch.delenv("DREAMNAV_FRAME_MAX_COUNT", raising=False)

    settings = default_settings()

    assert settings.processing.frame_timeout_sec == 45
    assert settings.processing.frame_rate == 4
    assert settings.processing.frame_max_count == 360
