from io import BytesIO
from pathlib import Path

import anyio
from fastapi import UploadFile

from app.config import ProcessingSettings
from app.jobs import JobRepository
from app.worker import ProcessingWorker


def test_worker_fails_colmap_backend_when_pose_outputs_are_missing(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    fake_colmap = tmp_path / "fake_colmap.py"
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "print('colmap command without sparse output')\n",
        encoding="utf-8",
    )
    fake_colmap.chmod(0o755)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            pose_backend="colmap",
            pose_command=str(fake_colmap),
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert status.state == "failed"
    assert status.failed_stage == "estimating_camera_motion"
    assert status.error_message == "COLMAP cameras.txt is missing."
