from __future__ import annotations

from dataclasses import asdict, dataclass
from json import JSONDecodeError, dumps, loads
from pathlib import Path
from re import sub
from secrets import token_hex
from shutil import copyfileobj
from time import time

from fastapi import UploadFile

from .schemas import JobStatus, UploadResponse

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
ESTIMATED_PROCESSING_TIME_SEC = 240
FEATURED_SCENE_MIN_GAUSSIANS = 12000
FEATURED_SCENE_MIN_OBSERVED_RATIO = 0.05
FEATURED_SCENE_MAX_COMPLETION_RATIO = 0.8


class JobNotFoundError(Exception):
    pass


class JobDataError(Exception):
    pass


class JobArtifactNotFoundError(Exception):
    pass


class JobArtifactNameError(Exception):
    pass


@dataclass(frozen=True)
class StoredJob:
    job_id: str
    original_filename: str
    stored_filename: str
    created_at_sec: float
    updated_at_sec: float
    state: str
    stage: str
    progress: float
    message: str
    validation_status: str
    warnings: list[str]
    estimated_processing_time_sec: int
    output_scene_id: str | None
    error_message: str | None
    failed_stage: str | None
    failed_artifact: str | None


@dataclass(frozen=True)
class ProcessingStep:
    stage: str
    progress: float
    message: str


class JobRepository:
    def __init__(
        self,
        jobs_root: Path,
        uploads_root: Path,
        now_func=time,
    ) -> None:
        self.jobs_root = jobs_root
        self.uploads_root = uploads_root
        self.now_func = now_func

    async def create_upload_job(self, upload: UploadFile) -> UploadResponse:
        job_id = self._new_job_id()
        job_root = self.uploads_root / job_id
        job_root.mkdir(parents=True, exist_ok=False)

        stored_filename = self._safe_filename(upload.filename or "walkthrough.mp4")
        stored_path = job_root / stored_filename
        with stored_path.open("wb") as output_file:
            copyfileobj(upload.file, output_file)

        warnings = self._validation_warnings(stored_filename, stored_path.stat().st_size)
        validation_status = "warning" if warnings else "pass"
        created_at_sec = self.now_func()
        job = StoredJob(
            job_id=job_id,
            original_filename=upload.filename or stored_filename,
            stored_filename=stored_filename,
            created_at_sec=created_at_sec,
            updated_at_sec=created_at_sec,
            state="queued",
            stage="checking_capture_quality",
            progress=0,
            message="Queued for processing",
            validation_status=validation_status,
            warnings=warnings,
            estimated_processing_time_sec=ESTIMATED_PROCESSING_TIME_SEC,
            output_scene_id=None,
            error_message=None,
            failed_stage=None,
            failed_artifact=None,
        )
        self._write_job(job)

        return UploadResponse(
            job_id=job.job_id,
            validation_status=job.validation_status,
            warnings=job.warnings,
            estimated_processing_time_sec=job.estimated_processing_time_sec,
        )

    def get_status(self, job_id: str) -> JobStatus:
        job = self._read_job(job_id)
        elapsed_sec = max(0, int(self.now_func() - job.created_at_sec))

        return JobStatus(
            job_id=job.job_id,
            state=job.state,
            stage=job.stage,
            progress=job.progress,
            elapsed_sec=elapsed_sec,
            message=job.message,
            output_scene_id=job.output_scene_id,
            error_message=job.error_message,
            failed_stage=job.failed_stage,
            failed_artifact=job.failed_artifact,
        )

    def get_job(self, job_id: str) -> StoredJob:
        return self._read_job(job_id)

    def claim_next_queued_job(self) -> StoredJob | None:
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.jobs_root.glob("scene_*.json")):
            job = self._read_job(path.stem)
            if job.state == "queued":
                running_job = self._replace_job(
                    job,
                    state="running",
                    updated_at_sec=self.now_func(),
                    message="Checking capture quality",
                )
                self._write_job(running_job)
                return running_job

        return None

    def update_stage(self, job_id: str, step: ProcessingStep) -> StoredJob:
        job = self._read_job(job_id)
        updated_job = self._replace_job(
            job,
            state="running",
            stage=step.stage,
            progress=step.progress,
            message=step.message,
            updated_at_sec=self.now_func(),
        )
        self._write_job(updated_job)
        return updated_job

    def complete_job(self, job_id: str, output_scene_id: str) -> StoredJob:
        job = self._read_job(job_id)
        completed_job = self._replace_job(
            job,
            state="completed",
            stage="completed",
            progress=1,
            message="Explorer ready",
            output_scene_id=output_scene_id,
            error_message=None,
            failed_stage=None,
            failed_artifact=None,
            updated_at_sec=self.now_func(),
        )
        self._write_job(completed_job)
        return completed_job

    def fail_job(
        self,
        job_id: str,
        error_message: str,
        failed_stage: str | None = None,
        failed_artifact: str | None = None,
    ) -> StoredJob:
        job = self._read_job(job_id)
        failed_job = self._replace_job(
            job,
            state="failed",
            stage="failed",
            progress=job.progress,
            message="Processing failed",
            error_message=error_message,
            failed_stage=failed_stage or job.stage,
            failed_artifact=failed_artifact,
            updated_at_sec=self.now_func(),
        )
        self._write_job(failed_job)
        return failed_job

    def artifact_root(self, job_id: str) -> Path:
        return self.jobs_root / job_id / "artifacts"

    def latest_completed_job_id(self) -> str | None:
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        completed_jobs = sorted(
            (self._read_job(path.stem) for path in self.jobs_root.glob("scene_*.json")),
            key=lambda job: job.updated_at_sec,
            reverse=True,
        )

        for job in completed_jobs:
            if job.state != "completed" or job.output_scene_id is None:
                continue

            if self._featured_scene_ready(job.job_id):
                return job.job_id

        return None

    def featured_scene_ready(self, job_id: str) -> bool:
        self._read_job(job_id)
        return self._featured_scene_ready(job_id)

    def write_artifact(self, job_id: str, artifact_name: str, payload: object) -> Path:
        artifact_root = self.artifact_root(job_id)
        artifact_root.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_root / artifact_name
        artifact_path.write_text(dumps(payload, indent=2), encoding="utf-8")
        return artifact_path

    def read_artifact(self, job_id: str, artifact_name: str) -> dict[str, object]:
        self._read_job(job_id)
        safe_artifact_name = self._safe_artifact_name(artifact_name)
        artifact_path = self.artifact_root(job_id) / safe_artifact_name

        try:
            payload = loads(artifact_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise JobArtifactNotFoundError(artifact_name) from error
        except JSONDecodeError as error:
            raise JobDataError(f"Invalid artifact data for {job_id}/{safe_artifact_name}") from error

        if not isinstance(payload, dict):
            raise JobDataError(f"Invalid artifact data for {job_id}/{safe_artifact_name}")

        return payload

    def upload_path(self, job: StoredJob) -> Path:
        return self.uploads_root / job.job_id / job.stored_filename

    def _new_job_id(self) -> str:
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        for _ in range(5):
            job_id = f"scene_{token_hex(4)}"
            if not (self.jobs_root / f"{job_id}.json").exists():
                return job_id

        raise JobDataError("Could not allocate a unique job id")

    def _write_job(self, job: StoredJob) -> None:
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        path = self.jobs_root / f"{job.job_id}.json"
        temp_path = path.with_suffix(".json.tmp")
        temp_path.write_text(dumps(asdict(job), indent=2), encoding="utf-8")
        temp_path.replace(path)

    def _read_job(self, job_id: str) -> StoredJob:
        try:
            payload = loads((self.jobs_root / f"{job_id}.json").read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("Job payload must be an object")
            payload = self._with_current_defaults(payload)
            return StoredJob(**payload)
        except FileNotFoundError as error:
            raise JobNotFoundError(job_id) from error
        except (JSONDecodeError, TypeError) as error:
            raise JobDataError(f"Invalid job data for {job_id}") from error

    def _validation_warnings(self, filename: str, file_size_bytes: int) -> list[str]:
        warnings = []

        if Path(filename).suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            warnings.append("Use MP4, MOV, or M4V walkthrough videos for reconstruction.")

        if file_size_bytes == 0:
            warnings.append("Uploaded file is empty.")

        return warnings

    def _safe_filename(self, filename: str) -> str:
        stem = Path(filename).stem or "walkthrough"
        suffix = Path(filename).suffix.lower() or ".mp4"
        safe_stem = sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "walkthrough"
        return f"{safe_stem}{suffix}"

    def _safe_artifact_name(self, artifact_name: str) -> str:
        artifact_path = Path(artifact_name)
        if artifact_path.name != artifact_name or artifact_path.suffix != ".json":
            raise JobArtifactNameError("Artifact name must be a job-local JSON file.")

        safe_name = sub(r"[^A-Za-z0-9_.-]+", "_", artifact_name)
        if safe_name != artifact_name or artifact_name.startswith("."):
            raise JobArtifactNameError("Artifact name must be a job-local JSON file.")

        return artifact_name

    def _replace_job(self, job: StoredJob, **changes: object) -> StoredJob:
        payload = asdict(job)
        payload.update(changes)
        return StoredJob(**payload)

    def _with_current_defaults(self, payload: dict[str, object]) -> dict[str, object]:
        created_at_sec = float(payload.get("created_at_sec", self.now_func()))
        return {
            **payload,
            "updated_at_sec": payload.get("updated_at_sec", created_at_sec),
            "state": payload.get("state", "queued"),
            "stage": payload.get("stage", "checking_capture_quality"),
            "progress": payload.get("progress", 0),
            "message": payload.get("message", "Queued for processing"),
            "output_scene_id": payload.get("output_scene_id", None),
            "error_message": payload.get("error_message", None),
            "failed_stage": payload.get("failed_stage", None),
            "failed_artifact": payload.get("failed_artifact", None),
        }

    def _featured_scene_ready(self, job_id: str) -> bool:
        artifacts_root = self.artifact_root(job_id)
        required_assets = [
            "camera_motion.json",
            "camera_path.json",
            "completion_manifest.json",
            "gaussian_scene.json",
            "metadata.json",
            "quality.json",
            "splat.ply",
            "visibility_manifest.json",
        ]
        if not all((artifacts_root / asset_name).is_file() for asset_name in required_assets):
            return False

        camera_motion = self.read_artifact(job_id, "camera_motion.json")
        gaussian_scene = self.read_artifact(job_id, "gaussian_scene.json")
        visibility_manifest = self.read_artifact(job_id, "visibility_manifest.json")
        quality_report = self.read_artifact(job_id, "quality.json")
        return (
            camera_motion.get("backend") != "stub"
            and gaussian_scene.get("backend") in {"command", "import"}
            and _float_value(gaussian_scene.get("gaussian_count")) >= FEATURED_SCENE_MIN_GAUSSIANS
            and _float_value(visibility_manifest.get("observed_ratio")) >= FEATURED_SCENE_MIN_OBSERVED_RATIO
            and _float_value(visibility_manifest.get("completion_candidate_ratio")) <= FEATURED_SCENE_MAX_COMPLETION_RATIO
            and quality_report.get("quality_gate") != "fail"
        )


def _float_value(value: object) -> float:
    if isinstance(value, bool):
        return 0

    if isinstance(value, (int, float)):
        return float(value)

    return 0
