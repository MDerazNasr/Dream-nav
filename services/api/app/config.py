from dataclasses import dataclass
from os import environ
from pathlib import Path
from shutil import which

DEFAULT_FRAME_TIMEOUT_SEC = 30
DEFAULT_POSE_TIMEOUT_SEC = 180
DEFAULT_GAUSSIAN_TIMEOUT_SEC = 60


@dataclass(frozen=True)
class ProcessingSettings:
    frame_backend: str = "stub"
    frame_command: str | None = None
    frame_timeout_sec: float = DEFAULT_FRAME_TIMEOUT_SEC
    frame_rate: float = 2
    frame_max_count: int = 240
    frame_max_duration_sec: float = 60
    pose_backend: str = "stub"
    pose_command: str | None = None
    pose_timeout_sec: float = DEFAULT_POSE_TIMEOUT_SEC
    gaussian_backend: str = "stub"
    gaussian_command: str | None = None
    gaussian_timeout_sec: float = DEFAULT_GAUSSIAN_TIMEOUT_SEC


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
    configured_frame_backend = environ.get("DREAMNAV_FRAME_BACKEND")
    resolved_frame_backend = configured_frame_backend or _default_frame_backend()
    resolved_frame_command = environ.get("DREAMNAV_FRAME_COMMAND")
    configured_pose_backend = environ.get("DREAMNAV_POSE_BACKEND")
    resolved_pose_backend = configured_pose_backend or _default_pose_backend()
    resolved_pose_command = environ.get("DREAMNAV_POSE_COMMAND")
    configured_gaussian_backend = environ.get("DREAMNAV_GAUSSIAN_BACKEND")
    resolved_gaussian_backend = configured_gaussian_backend or _default_gaussian_backend(resolved_pose_backend)
    resolved_gaussian_command = environ.get("DREAMNAV_GAUSSIAN_COMMAND")

    if resolved_frame_backend == "ffmpeg" and not resolved_frame_command:
        resolved_frame_command = which("ffmpeg")

    if resolved_pose_backend == "colmap" and not resolved_pose_command:
        resolved_pose_command = which("colmap")

    if resolved_gaussian_backend == "command" and not resolved_gaussian_command:
        resolved_gaussian_command = _default_gaussian_command(resolved_pose_backend)

    return ApiSettings(
        repo_root=Path(__file__).resolve().parents[3],
        processing=ProcessingSettings(
            frame_backend=resolved_frame_backend,
            frame_command=resolved_frame_command,
            frame_timeout_sec=float(environ.get("DREAMNAV_FRAME_TIMEOUT_SEC", str(DEFAULT_FRAME_TIMEOUT_SEC))),
            frame_rate=float(environ.get("DREAMNAV_FRAME_RATE", "2")),
            frame_max_count=int(environ.get("DREAMNAV_FRAME_MAX_COUNT", "240")),
            frame_max_duration_sec=float(environ.get("DREAMNAV_FRAME_MAX_DURATION_SEC", "60")),
            pose_backend=resolved_pose_backend,
            pose_command=resolved_pose_command,
            pose_timeout_sec=float(environ.get("DREAMNAV_POSE_TIMEOUT_SEC", str(DEFAULT_POSE_TIMEOUT_SEC))),
            gaussian_backend=resolved_gaussian_backend,
            gaussian_command=resolved_gaussian_command,
            gaussian_timeout_sec=float(environ.get("DREAMNAV_GAUSSIAN_TIMEOUT_SEC", str(DEFAULT_GAUSSIAN_TIMEOUT_SEC))),
        ),
    )


def _default_frame_backend() -> str:
    return "ffmpeg" if which("ffmpeg") else "stub"


def _default_pose_backend() -> str:
    return "colmap" if which("colmap") else "stub"


def _default_gaussian_backend(pose_backend: str) -> str:
    return "command" if pose_backend == "colmap" and _internal_gaussian_wrapper_path().is_file() else "stub"


def _default_gaussian_command(pose_backend: str) -> str | None:
    if pose_backend != "colmap":
        return None

    wrapper = _internal_gaussian_wrapper_path()
    return str(wrapper) if wrapper.is_file() else None


def _internal_gaussian_wrapper_path() -> Path:
    return Path(__file__).with_name("colmap_sparse_to_splat.py")
