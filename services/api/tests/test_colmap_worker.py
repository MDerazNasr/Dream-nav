from io import BytesIO
from json import loads
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
    assert status.failed_artifact == "colmap_model_selection_command.json"
    assert "exit code 1" in (status.error_message or "")


def test_worker_stops_at_failed_colmap_pipeline_step(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    fake_colmap = tmp_path / "fake_colmap.py"
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('fake colmap ' + sys.argv[1])\n"
        "if sys.argv[1] == 'exhaustive_matcher':\n"
        "    sys.exit(7)\n",
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
    artifact_root = tmp_path / "data" / "jobs" / response.job_id / "artifacts"
    matcher_artifact = loads(
        (artifact_root / "colmap_exhaustive_matcher_command.json").read_text(encoding="utf-8")
    )

    assert status.state == "failed"
    assert status.failed_artifact == "colmap_exhaustive_matcher_command.json"
    assert "exit code 7" in (status.error_message or "")
    assert matcher_artifact["exit_code"] == 7
    assert not (artifact_root / "colmap_mapper_command.json").exists()
