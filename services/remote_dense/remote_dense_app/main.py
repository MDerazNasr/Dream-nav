from __future__ import annotations

from dataclasses import dataclass
from os import environ
from pathlib import Path
from secrets import token_hex

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from .generator import (
    RemoteDenseGenerationError,
    bundle_manifest,
    generate_mock_dense_ply,
    write_submission_bundle,
)


@dataclass(frozen=True)
class RemoteDenseSettings:
    repo_root: Path
    callback_timeout_sec: float = 30

    @property
    def submissions_root(self) -> Path:
        return self.repo_root / ".context" / "remote-dense-submissions"


def default_settings() -> RemoteDenseSettings:
    return RemoteDenseSettings(
        repo_root=Path(__file__).resolve().parents[3],
        callback_timeout_sec=float(environ.get("DREAMNAV_REMOTE_DENSE_CALLBACK_TIMEOUT_SEC", "30")),
    )


def create_app(settings: RemoteDenseSettings | None = None) -> FastAPI:
    resolved_settings = settings or default_settings()
    app = FastAPI(title="DreamNav Remote Dense Worker", version="0.1.0")
    app.state.settings = resolved_settings
    app.state.callback_sender = _post_dense_callback

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "dreamnav-remote-dense"}

    @app.post("/jobs")
    async def submit_job(
        background_tasks: BackgroundTasks,
        job_id: str = Form(...),
        callback_url: str = Form(...),
        callback_token: str = Form(...),
        source_video: str = Form(...),
        bundle: UploadFile = File(...),
    ) -> dict[str, object]:
        bundle_bytes = await bundle.read()
        remote_job_id = f"remote_{token_hex(4)}"

        try:
            manifest = bundle_manifest(bundle_bytes)
            dense_ply = generate_mock_dense_ply(bundle_bytes)
            submission_bundle = write_submission_bundle(
                resolved_settings.submissions_root,
                remote_job_id,
                bundle_bytes,
            )
        except RemoteDenseGenerationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        background_tasks.add_task(
            app.state.callback_sender,
            callback_url,
            callback_token,
            dense_ply,
            remote_job_id,
            resolved_settings.callback_timeout_sec,
        )

        return {
            "job_id": job_id,
            "remote_job_id": remote_job_id,
            "submission_status": "submitted",
            "source_video": source_video,
            "bundle_file": submission_bundle.name,
            "bundle_size_bytes": submission_bundle.stat().st_size,
            "frame_count": manifest.get("frame_count", 0),
        }

    return app


def _post_dense_callback(
    callback_url: str,
    callback_token: str,
    dense_ply: bytes,
    remote_job_id: str,
    timeout_sec: float,
) -> None:
    with httpx.Client(timeout=timeout_sec) as client:
        response = client.post(
            callback_url,
            headers={"X-DreamNav-Callback-Token": callback_token},
            files={"file": (f"{remote_job_id}.ply", dense_ply, "application/octet-stream")},
        )
        response.raise_for_status()


app = create_app()
