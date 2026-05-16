from io import BytesIO
from pathlib import Path
import sys

import anyio
from fastapi import UploadFile

from app.camera_processing import build_camera_motion_command
from app.config import ProcessingSettings
from app.jobs import JobRepository
from app.processing_models import ProcessingTaskContext


def test_build_camera_motion_command_extends_mapper_timeout_for_longer_clips(tmp_path: Path) -> None:
    repo, job_id = _uploaded_job(tmp_path)
    artifacts_root = repo.artifact_root(job_id)
    frames_root = artifacts_root / "frames"
    frames_root.mkdir(parents=True, exist_ok=True)
    for frame_index in range(59):
        (frames_root / f"frame_{frame_index + 1:04d}.jpg").write_bytes(b"\xff\xd8\xff\xd9")

    commands = build_camera_motion_command(
        ProcessingTaskContext(
            job=repo.get_job(job_id),
            upload_path=repo.upload_path(repo.get_job(job_id)),
                artifacts_root=artifacts_root,
                processing_settings=ProcessingSettings(
                    pose_backend="colmap",
                    pose_command=sys.executable,
                    pose_timeout_sec=180,
                ),
            )
    )

    assert isinstance(commands, list)
    mapper_command = next(command for command in commands if command.artifact_name == "colmap_mapper_command.json")
    feature_command = next(
        command for command in commands if command.artifact_name == "colmap_feature_extractor_command.json"
    )
    assert mapper_command.timeout_sec == 300
    assert feature_command.timeout_sec == 180


def test_build_camera_motion_command_keeps_configured_timeout_for_short_mapper_runs(tmp_path: Path) -> None:
    repo, job_id = _uploaded_job(tmp_path)
    artifacts_root = repo.artifact_root(job_id)
    frames_root = artifacts_root / "frames"
    frames_root.mkdir(parents=True, exist_ok=True)
    for frame_index in range(3):
        (frames_root / f"frame_{frame_index + 1:04d}.jpg").write_bytes(b"\xff\xd8\xff\xd9")

    commands = build_camera_motion_command(
        ProcessingTaskContext(
            job=repo.get_job(job_id),
            upload_path=repo.upload_path(repo.get_job(job_id)),
                artifacts_root=artifacts_root,
                processing_settings=ProcessingSettings(
                    pose_backend="colmap",
                    pose_command=sys.executable,
                    pose_timeout_sec=420,
                ),
            )
    )

    assert isinstance(commands, list)
    mapper_command = next(command for command in commands if command.artifact_name == "colmap_mapper_command.json")
    assert mapper_command.timeout_sec == 420


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
