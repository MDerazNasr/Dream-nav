from pathlib import Path
from io import BytesIO
from json import dumps

import anyio
from fastapi import UploadFile

from app.jobs import JobRepository
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
