from pathlib import Path
from io import BytesIO
from json import dumps, loads
import sys

import anyio
from fastapi import UploadFile

from app.config import ProcessingSettings
from app.jobs import JobRepository, ProcessingStep
from app.processing_tasks import (
    ProcessingCommand,
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
    capture_quality = loads(artifact_path.read_text(encoding="utf-8"))
    assert capture_quality["job_id"] == response.job_id
    assert capture_quality["file_size_bytes"] == len(b"video-bytes")
    assert capture_quality["extension"] == ".mp4"
    command_path = (
        tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "camera_motion_command.json"
    )
    frame_artifact_path = (
        tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "frame_extraction.json"
    )
    frame_command_path = (
        tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "frame_extraction_command.json"
    )
    frames_root = tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "frames"
    frame_artifact = loads(frame_artifact_path.read_text(encoding="utf-8"))
    command_artifact = loads(command_path.read_text(encoding="utf-8"))
    frame_command = loads(frame_command_path.read_text(encoding="utf-8"))
    assert frame_artifact["backend"] == "stub"
    assert frame_artifact["frame_count"] == 3
    assert (frames_root / "frame_0000.jpg").is_file()
    assert "frame_backend=stub" in frame_command["stdout"]
    assert command_artifact["exit_code"] == 0
    assert "pose_backend=stub" in command_artifact["stdout"]
    camera_motion_path = tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "camera_motion.json"
    camera_motion = loads(camera_motion_path.read_text(encoding="utf-8"))
    assert camera_motion["backend"] == "stub"
    assert camera_motion["command_mode"] == "stub"


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


def test_worker_fails_job_when_task_command_fails(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(repo, tasks=[_command_failing_task()], step_delay_sec=0)

    worker.process_next_job()
    status = repo.get_status(response.job_id)
    command_path = tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "bad_command.json"
    command_artifact = loads(command_path.read_text(encoding="utf-8"))

    assert status.state == "failed"
    assert status.error_message is not None
    assert "exit code 12" in status.error_message
    assert command_artifact["exit_code"] == 12


def test_worker_fails_when_colmap_backend_is_missing(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            pose_backend="colmap",
            pose_command=str(tmp_path / "missing_colmap"),
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert status.state == "failed"
    assert status.error_message == "Pose backend colmap selected but COLMAP binary was not found."


def test_worker_runs_configured_colmap_command(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    fake_colmap = tmp_path / "fake_colmap.py"
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('fake colmap ' + ' '.join(sys.argv[1:]))\n",
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
            pose_timeout_sec=5,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)
    command_path = (
        tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "camera_motion_command.json"
    )
    command_artifact = loads(command_path.read_text(encoding="utf-8"))
    camera_motion = loads(
        (tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "camera_motion.json").read_text(
            encoding="utf-8"
        )
    )

    assert status.state == "completed"
    assert command_artifact["exit_code"] == 0
    assert command_artifact["command"][0] == str(fake_colmap)
    assert "feature_extractor" in command_artifact["stdout"]
    assert camera_motion["backend"] == "colmap"
    assert camera_motion["command_mode"] == "external"
    assert str(tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "frames") in command_artifact["command"]


def test_worker_fails_when_ffmpeg_backend_is_missing(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            frame_backend="ffmpeg",
            frame_command=str(tmp_path / "missing_ffmpeg"),
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert status.state == "failed"
    assert status.error_message == "Frame backend ffmpeg selected but ffmpeg binary was not found."


def test_worker_runs_configured_ffmpeg_command(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    fake_ffmpeg = tmp_path / "fake_ffmpeg.py"
    fake_ffmpeg.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[-1].replace('%04d', '0001')).write_text('frame')\n"
        "print('fake ffmpeg ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_ffmpeg.chmod(0o755)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            frame_backend="ffmpeg",
            frame_command=str(fake_ffmpeg),
            frame_rate=4,
            frame_timeout_sec=5,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)
    frame_command = loads(
        (
            tmp_path
            / "data"
            / "jobs"
            / response.job_id
            / "artifacts"
            / "frame_extraction_command.json"
        ).read_text(encoding="utf-8")
    )
    frame_artifact = loads(
        (
            tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "frame_extraction.json"
        ).read_text(encoding="utf-8")
    )

    assert status.state == "completed"
    assert frame_command["exit_code"] == 0
    assert frame_command["command"][0] == str(fake_ffmpeg)
    assert "fps=4" in frame_command["command"]
    assert frame_artifact["backend"] == "ffmpeg"
    assert frame_artifact["command_mode"] == "external"
    assert frame_artifact["frame_count"] == 1


def test_worker_fails_empty_capture_validation(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"")),
    )
    worker = ProcessingWorker(repo, step_delay_sec=0)

    worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert status.state == "failed"
    assert status.error_message == "Uploaded file is empty."


def test_worker_records_unsupported_extension_warning(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.txt", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(repo, step_delay_sec=0)

    worker.process_next_job()
    artifact_path = tmp_path / "data" / "jobs" / response.job_id / "artifacts" / "capture_quality.json"
    capture_quality = loads(artifact_path.read_text(encoding="utf-8"))

    assert capture_quality["validation_status"] == "warning"
    assert "Use MP4, MOV, or M4V walkthrough videos for reconstruction." in capture_quality["warnings"]


def _failing_task() -> ProcessingTask:
    def run(context: ProcessingTaskContext) -> ProcessingTaskResult:
        del context
        raise ProcessingTaskFailed("camera motion failed")

    return ProcessingTask(
        step=ProcessingStep("estimating_camera_motion", 0.2, "Estimating camera motion"),
        artifact_name="camera_motion.json",
        run=run,
    )


def _command_failing_task() -> ProcessingTask:
    def run(context: ProcessingTaskContext) -> ProcessingTaskResult:
        return ProcessingTaskResult("bad.json", {"job_id": context.job.job_id})

    def command_builder(context: ProcessingTaskContext) -> ProcessingCommand:
        del context
        return ProcessingCommand(
            artifact_name="bad_command.json",
            command=[sys.executable, "-c", "import sys; print('failed', file=sys.stderr); sys.exit(12)"],
            timeout_sec=5,
        )

    return ProcessingTask(
        step=ProcessingStep("estimating_camera_motion", 0.2, "Estimating camera motion"),
        artifact_name="bad.json",
        run=run,
        command_builder=command_builder,
    )
