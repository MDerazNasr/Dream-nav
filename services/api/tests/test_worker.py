from pathlib import Path
from io import BytesIO
from json import dumps, loads

import anyio
from fastapi import UploadFile

from app.jobs import JobRepository, ProcessingStep
from app.processing_tasks import (
    ProcessingTask,
    ProcessingTaskContext,
    ProcessingTaskFailed,
    ProcessingTaskResult,
)
from app.worker import ProcessingWorker


def test_worker_completes_queued_job(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    upload = UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes"))
    response = anyio.run(repo.create_upload_job, upload)
    worker = ProcessingWorker(repo, step_delay_sec=0)

    processed_job_id = worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert processed_job_id == response.job_id
    assert status.state == "completed"
    assert status.stage == "completed"
    assert status.progress == 1
    assert status.output_scene_id == "warehouse_01"
    artifact_path = tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "capture_quality.json"
    assert artifact_path.is_file()
    assert loads(artifact_path.read_text(encoding="utf-8"))["job_id"] == response.job_id


def test_worker_reads_legacy_elapsed_time_job(tmp_path: Path) -> None:
    jobs_root = tmp_path / "data" / "jobs"
    jobs_root.mkdir(parents=True)
    (jobs_root / "scene_legacy.json").write_text(
        dumps(
            {
                "job_id": "scene_legacy",
                "original_filename": "walkthrough.mp4",
                "stored_filename": "walkthrough.mp4",
                "created_at_sec": 10,
                "validation_status": "pass",
                "warnings": [],
                "estimated_processing_time_sec": 240,
            }
        ),
        encoding="utf-8",
    )
    upload_root = tmp_path / "data" / "uploads" / "scene_legacy"
    upload_root.mkdir(parents=True)
    (upload_root / "walkthrough.mp4").write_bytes(b"video-bytes")
    repo = JobRepository(jobs_root=jobs_root, uploads_root=tmp_path / "data" / "uploads")
    worker = ProcessingWorker(repo, step_delay_sec=0)

    processed_job_id = worker.process_next_job()
    status = repo.get_status("scene_legacy")

    assert processed_job_id == "scene_legacy"
    assert status.state == "completed"


def test_worker_drains_all_queued_jobs(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    first = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="first.mp4", file=BytesIO(b"first-video")),
    )
    second = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="second.mp4", file=BytesIO(b"second-video")),
    )
    worker = ProcessingWorker(repo, step_delay_sec=0)

    processed_job_ids = worker.process_available_jobs()

    assert set(processed_job_ids) == {first.job_id, second.job_id}
    assert repo.get_status(second.job_id).state == "completed"


def test_worker_fails_job_when_task_fails(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(repo, tasks=[_failing_task()], step_delay_sec=0)

    processed_job_id = worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert processed_job_id == response.job_id
    assert status.state == "failed"
    assert status.stage == "failed"
    assert status.error_message == "camera motion failed"


def _failing_task() -> ProcessingTask:
    def run(context: ProcessingTaskContext) -> ProcessingTaskResult:
        del context
        raise ProcessingTaskFailed("camera motion failed")

    return ProcessingTask(
        step=ProcessingStep("estimating_camera_motion", 0.2, "Estimating camera motion"),
        artifact_name="camera_motion.json",
        run=run,
    )
