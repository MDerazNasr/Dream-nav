from app.config import ProcessingSettings
from app.reconstruction_capabilities import detect_reconstruction_capabilities


def test_detect_reconstruction_capabilities_reports_stub_pipeline() -> None:
    capabilities = detect_reconstruction_capabilities(ProcessingSettings())

    assert capabilities.pipeline_status == "stub"
    assert capabilities.real_reconstruction_ready is False
    assert "Set DREAMNAV_FRAME_BACKEND=ffmpeg to extract real video frames." in capabilities.missing_requirements


def test_detect_reconstruction_capabilities_reports_mixed_pipeline() -> None:
    capabilities = detect_reconstruction_capabilities(
        ProcessingSettings(
            frame_backend="ffmpeg",
            frame_command="/opt/homebrew/bin/ffmpeg",
            pose_backend="stub",
            gaussian_backend="stub",
        )
    )

    assert capabilities.pipeline_status == "mixed"
    assert capabilities.frame_command == "/opt/homebrew/bin/ffmpeg"
    assert capabilities.pose_command is None
    assert capabilities.gaussian_command is None

