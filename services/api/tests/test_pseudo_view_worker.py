from io import BytesIO
from json import loads
from pathlib import Path

import anyio
from fastapi import UploadFile

from app.jobs import JobRepository
from app.worker import ProcessingWorker


def test_worker_writes_pseudo_view_training_artifacts(tmp_path: Path) -> None:
    repo = JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(repo, step_delay_sec=0)

    worker.process_next_job()

    training_views = _artifact(tmp_path, response.job_id, "training_views.json")
    pseudo_views = _artifact(tmp_path, response.job_id, "pseudo_views.json")
    first_view = pseudo_views["views"][0]

    assert training_views["renderer"] == "placeholder_splat_renderer_v1"
    assert training_views["train_views"] == 9
    assert training_views["heldout_views"] == 3
    assert pseudo_views["train_views"] == training_views["train_views"]
    assert pseudo_views["heldout_views"] == training_views["heldout_views"]
    assert (tmp_path / "data" / "jobs" / response.job_id / "artifacts" / first_view["rgb_path"]).is_file()
    assert (tmp_path / "data" / "jobs" / response.job_id / "artifacts" / first_view["depth_path"]).is_file()


def _artifact(tmp_path: Path, job_id: str, artifact_name: str) -> dict[str, object]:
    artifact_path = tmp_path / "data" / "jobs" / job_id / "artifacts" / artifact_name
    return loads(artifact_path.read_text(encoding="utf-8"))
