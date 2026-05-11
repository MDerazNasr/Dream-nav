from pathlib import Path
from io import BytesIO
from json import loads

import anyio
from fastapi import UploadFile

from app.config import ProcessingSettings
from app.jobs import JobRepository
from app.worker import ProcessingWorker


def test_worker_runs_configured_gaussian_command(tmp_path: Path) -> None:
    repo = _job_repository(tmp_path)
    fake_gaussian = tmp_path / "fake_gaussian.py"
    fake_gaussian.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        "output = Path(sys.argv[sys.argv.index('--output-splat') + 1])\n"
        "output.write_bytes(b'ply\\nformat ascii 1.0\\nelement vertex 4\\nend_header\\n')\n"
        "print('fake gaussian ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_gaussian.chmod(0o755)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            gaussian_backend="command",
            gaussian_command=str(fake_gaussian),
            gaussian_timeout_sec=5,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)
    command_artifact = _read_job_artifact(tmp_path, response.job_id, "gaussian_scene_command.json")
    gaussian_scene = _read_job_artifact(tmp_path, response.job_id, "gaussian_scene.json")

    assert status.state == "completed"
    assert command_artifact["command"][0] == str(fake_gaussian)
    assert "--output-splat" in command_artifact["command"]
    assert gaussian_scene["backend"] == "command"
    assert gaussian_scene["command_mode"] == "external"
    assert gaussian_scene["gaussian_count"] == 4
    assert gaussian_scene["splat_source"] == "existing"


def test_worker_fails_when_gaussian_command_is_missing(tmp_path: Path) -> None:
    repo = _job_repository(tmp_path)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            gaussian_backend="command",
            gaussian_command=str(tmp_path / "missing_gaussian"),
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert status.state == "failed"
    assert status.failed_stage == "building_gaussian_scene"
    assert status.error_message == "Gaussian backend command selected but DREAMNAV_GAUSSIAN_COMMAND was not found."


def test_worker_fails_when_gaussian_command_skips_splat(tmp_path: Path) -> None:
    repo = _job_repository(tmp_path)
    fake_gaussian = tmp_path / "fake_gaussian_no_output.py"
    fake_gaussian.write_text(
        "#!/usr/bin/env python3\n"
        "print('no splat written')\n",
        encoding="utf-8",
    )
    fake_gaussian.chmod(0o755)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            gaussian_backend="command",
            gaussian_command=str(fake_gaussian),
            gaussian_timeout_sec=5,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert status.state == "failed"
    assert status.failed_stage == "building_gaussian_scene"
    assert status.error_message == "Gaussian reconstruction did not produce splat.ply."


def _job_repository(tmp_path: Path) -> JobRepository:
    return JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )


def _read_job_artifact(tmp_path: Path, job_id: str, artifact_name: str) -> dict[str, object]:
    artifact_path = tmp_path / "data" / "jobs" / job_id / "artifacts" / artifact_name
    return loads(artifact_path.read_text(encoding="utf-8"))
