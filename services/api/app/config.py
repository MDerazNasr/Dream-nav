from dataclasses import dataclass
from os import environ
from pathlib import Path


@dataclass(frozen=True)
class ProcessingSettings:
    frame_backend: str = "stub"
    frame_command: str | None = None
    frame_timeout_sec: float = 30
    frame_rate: float = 2
    frame_max_count: int = 240
    frame_max_duration_sec: float = 60
    pose_backend: str = "stub"
    pose_command: str | None = None
    pose_timeout_sec: float = 30
    gaussian_backend: str = "stub"
    gaussian_command: str | None = None
    gaussian_timeout_sec: float = 60


@dataclass(frozen=True)
class ApiSettings:
    repo_root: Path
    auto_start_worker: bool = True
    processing: ProcessingSettings = ProcessingSettings()

    @property
    def data_root(self) -> Path:
        return self.repo_root / "data"

    @property
    def scenes_root(self) -> Path:
        return self.data_root / "scenes"

    @property
    def jobs_root(self) -> Path:
        return self.data_root / "jobs"

    @property
    def uploads_root(self) -> Path:
        return self.data_root / "uploads"


def default_settings() -> ApiSettings:
    return ApiSettings(
        repo_root=Path(__file__).resolve().parents[3],
        processing=ProcessingSettings(
            frame_backend=environ.get("DREAMNAV_FRAME_BACKEND", "stub"),
            frame_command=environ.get("DREAMNAV_FRAME_COMMAND"),
            frame_timeout_sec=float(environ.get("DREAMNAV_FRAME_TIMEOUT_SEC", "30")),
            frame_rate=float(environ.get("DREAMNAV_FRAME_RATE", "2")),
            frame_max_count=int(environ.get("DREAMNAV_FRAME_MAX_COUNT", "240")),
            frame_max_duration_sec=float(environ.get("DREAMNAV_FRAME_MAX_DURATION_SEC", "60")),
            pose_backend=environ.get("DREAMNAV_POSE_BACKEND", "stub"),
            pose_command=environ.get("DREAMNAV_POSE_COMMAND"),
            pose_timeout_sec=float(environ.get("DREAMNAV_POSE_TIMEOUT_SEC", "30")),
            gaussian_backend=environ.get("DREAMNAV_GAUSSIAN_BACKEND", "stub"),
            gaussian_command=environ.get("DREAMNAV_GAUSSIAN_COMMAND"),
            gaussian_timeout_sec=float(environ.get("DREAMNAV_GAUSSIAN_TIMEOUT_SEC", "60")),
        ),
    )
