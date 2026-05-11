from io import BytesIO
from json import loads
from pathlib import Path

import anyio
from fastapi import UploadFile

from app.jobs import JobRepository
from app.worker import ProcessingWorker


def test_worker_writes_completion_dataset_artifact(tmp_path: Path) -> None:
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

    dataset = _artifact(tmp_path, response.job_id, "completion_dataset.json")
    scene_model = _artifact(tmp_path, response.job_id, "scene_model.json")

    assert dataset["dataset_version"] == "completion_dataset_v1"
    assert dataset["train_examples"] == 9
    assert dataset["heldout_examples"] == 3
    assert dataset["examples"][0]["references"]
    assert scene_model["dataset_manifest"] == "completion_dataset.json"
    assert scene_model["train_examples"] == dataset["train_examples"]


def _artifact(tmp_path: Path, job_id: str, artifact_name: str) -> dict[str, object]:
    artifact_path = tmp_path / "data" / "jobs" / job_id / "artifacts" / artifact_name
    return loads(artifact_path.read_text(encoding="utf-8"))
