from io import BytesIO
from json import loads
from pathlib import Path

import anyio
from fastapi import UploadFile

from app.config import ProcessingSettings
from app.jobs import JobRepository
from app.worker import ProcessingWorker


def test_worker_fails_when_ffmpeg_writes_no_frames(tmp_path: Path) -> None:
    fake_ffmpeg = _fake_ffmpeg(tmp_path, "print('no frames')\n")
    repo, job_id = _uploaded_job(tmp_path)
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(frame_backend="ffmpeg", frame_command=str(fake_ffmpeg)),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(job_id)
    frame_command = _artifact(tmp_path, job_id, "frame_extraction_command.json")

    assert status.state == "failed"
    assert status.error_message == "Frame extraction produced no JPG frames."
    assert frame_command["exit_code"] == 0


def test_worker_fails_when_ffmpeg_writes_non_jpeg_frame(tmp_path: Path) -> None:
    fake_ffmpeg = _fake_ffmpeg(
        tmp_path,
        "Path(sys.argv[-1].replace('%04d', '0001')).write_text('not jpeg')\n",
    )
    repo, job_id = _uploaded_job(tmp_path)
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(frame_backend="ffmpeg", frame_command=str(fake_ffmpeg)),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(job_id)

    assert status.state == "failed"
    assert status.error_message == "Extracted frame is not a JPEG file: frame_0001.jpg"


def test_worker_fails_when_ffmpeg_writes_too_many_frames(tmp_path: Path) -> None:
    fake_ffmpeg = _fake_ffmpeg(
        tmp_path,
        "for index in range(1, 4):\n"
        "    Path(sys.argv[-1].replace('%04d', f'{index:04d}')).write_bytes(b'\\xff\\xd8\\xff\\xd9')\n",
    )
    repo, job_id = _uploaded_job(tmp_path)
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            frame_backend="ffmpeg",
            frame_command=str(fake_ffmpeg),
            frame_max_count=2,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(job_id)

    assert status.state == "failed"
    assert status.error_message == "Frame extraction produced 3 frames, above configured limit 2."


def test_worker_fails_invalid_frame_settings_before_command(tmp_path: Path) -> None:
    repo, job_id = _uploaded_job(tmp_path)
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(frame_backend="ffmpeg", frame_rate=0),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(job_id)

    assert status.state == "failed"
    assert status.error_message == "Frame rate must be greater than zero."
    assert not (tmp_path / "data" / "jobs" / job_id / "artifacts" / "frame_extraction_command.json").exists()


def test_worker_records_frame_limit_warning(tmp_path: Path) -> None:
    fake_ffmpeg = _fake_ffmpeg(
        tmp_path,
        "for index in range(1, 3):\n"
        "    Path(sys.argv[-1].replace('%04d', f'{index:04d}')).write_bytes(b'\\xff\\xd8\\xff\\xd9')\n",
    )
    repo, job_id = _uploaded_job(tmp_path)
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            frame_backend="ffmpeg",
            frame_command=str(fake_ffmpeg),
            frame_max_count=2,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(job_id)
    frame_artifact = _artifact(tmp_path, job_id, "frame_extraction.json")

    assert status.state == "completed"
    assert frame_artifact["frame_count"] == 2
    assert "Frame extraction reached the configured frame limit." in frame_artifact["warnings"]


def _uploaded_job(tmp_path: Path) -> tuple[JobRepository, str]:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    return repo, response.job_id


def _fake_ffmpeg(tmp_path: Path, body: str) -> Path:
    fake_ffmpeg = tmp_path / "fake_ffmpeg.py"
    fake_ffmpeg.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        f"{body}"
        "print('fake ffmpeg ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_ffmpeg.chmod(0o755)
    return fake_ffmpeg


def _artifact(tmp_path: Path, job_id: str, artifact_name: str) -> dict[str, object]:
    artifact_path = tmp_path / "data" / "jobs" / job_id / "artifacts" / artifact_name
    return loads(artifact_path.read_text(encoding="utf-8"))
