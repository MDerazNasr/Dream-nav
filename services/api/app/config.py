from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiSettings:
    repo_root: Path
    auto_start_worker: bool = True

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
    return ApiSettings(repo_root=Path(__file__).resolve().parents[3])
