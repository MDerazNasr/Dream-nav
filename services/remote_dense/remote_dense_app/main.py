from __future__ import annotations

from dataclasses import dataclass
from json import dumps
from os import environ
from pathlib import Path
from secrets import token_hex

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from .backend import RemoteDenseBackendError, build_dense_result
from .generator import RemoteDenseGenerationError, bundle_manifest, write_submission_bundle


@dataclass(frozen=True)
class RemoteDenseSettings:
    repo_root: Path
    callback_timeout_sec: float = 30
    backend: str = "auto"
    colmap_command: str | None = None
    dense_command: str | None = None
    allow_mock_fallback: bool = True
    retained_job_count: int = 8

    @property
    def submissions_root(self) -> Path:
        return self.repo_root / ".context" / "remote-dense-submissions"


def default_settings() -> RemoteDenseSettings:
    return RemoteDenseSettings(
        repo_root=Path(__file__).resolve().parents[3],
        callback_timeout_sec=float(environ.get("DREAMNAV_REMOTE_DENSE_CALLBACK_TIMEOUT_SEC", "30")),
        backend=environ.get("DREAMNAV_REMOTE_DENSE_BACKEND", "auto"),
        colmap_command=environ.get("DREAMNAV_REMOTE_DENSE_COLMAP_COMMAND"),
        dense_command=environ.get("DREAMNAV_REMOTE_DENSE_COMMAND") or _default_dense_command(),
        allow_mock_fallback=environ.get("DREAMNAV_REMOTE_DENSE_ALLOW_MOCK_FALLBACK", "1") != "0",
        retained_job_count=max(1, int(environ.get("DREAMNAV_REMOTE_DENSE_RETAINED_JOBS", "8"))),
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
            submission_bundle = write_submission_bundle(
                resolved_settings.submissions_root,
                remote_job_id,
                bundle_bytes,
                resolved_settings.retained_job_count,
            )
            dense_result = build_dense_result(
                submission_bundle,
                submission_bundle.parent,
                resolved_settings.backend,
                resolved_settings.colmap_command,
                resolved_settings.dense_command,
                resolved_settings.allow_mock_fallback,
            )
        except RemoteDenseGenerationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except RemoteDenseBackendError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        background_tasks.add_task(
            app.state.callback_sender,
            callback_url,
            callback_token,
            dense_result.dense_ply,
            remote_job_id,
            dense_result.backend,
            resolved_settings.callback_timeout_sec,
        )

        _write_job_result_metadata(
            submission_bundle.parent,
            manifest,
            dense_result.backend,
            dense_result.warnings,
        )

        return _submission_response(
            job_id=job_id,
            remote_job_id=remote_job_id,
            submission_status="submitted",
            source_video=source_video,
            bundle_file=submission_bundle.name,
            bundle_size_bytes=submission_bundle.stat().st_size,
            frame_count=manifest.get("frame_count", 0),
            backend=dense_result.backend,
            warnings=dense_result.warnings,
        )

    return app


def _submission_response(
    job_id: str,
    remote_job_id: str,
    submission_status: str,
    source_video: str,
    bundle_file: str,
    bundle_size_bytes: int,
    frame_count: int,
    backend: str,
    warnings: list[str],
) -> dict[str, object]:
    return {
        "job_id": job_id,
        "remote_job_id": remote_job_id,
        "submission_status": submission_status,
        "source_video": source_video,
        "bundle_file": bundle_file,
        "bundle_size_bytes": bundle_size_bytes,
        "frame_count": frame_count,
        "backend": backend,
        "warnings": warnings,
    }


def _post_dense_callback(
    callback_url: str,
    callback_token: str,
    dense_ply: bytes,
    remote_job_id: str,
    backend: str,
    timeout_sec: float,
) -> None:
    with httpx.Client(timeout=timeout_sec) as client:
        response = client.post(
            callback_url,
            headers={
                "X-DreamNav-Callback-Token": callback_token,
                "X-DreamNav-Remote-Backend": backend,
                "X-DreamNav-Remote-Job-Id": remote_job_id,
            },
            files={"file": (f"{remote_job_id}.ply", dense_ply, "application/octet-stream")},
        )
        response.raise_for_status()


def _write_job_result_metadata(
    job_root: Path,
    manifest: dict[str, object],
    backend: str,
    warnings: list[str],
) -> None:
    payload = {
        "job_id": manifest.get("job_id"),
        "source_video": manifest.get("source_video"),
        "frame_count": manifest.get("frame_count"),
        "backend": backend,
        "warnings": warnings,
    }
    (job_root / "result.json").write_text(dumps(payload, indent=2), encoding="utf-8")


def _default_dense_command() -> str | None:
    adapter_path = Path(__file__).with_name("colmap_command_adapter.py")
    return str(adapter_path) if adapter_path.is_file() else None


app = create_app()
