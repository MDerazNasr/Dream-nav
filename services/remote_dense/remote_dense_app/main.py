from __future__ import annotations

from dataclasses import dataclass
from json import dumps, loads
from os import environ
from pathlib import Path
from secrets import token_hex
from threading import Semaphore

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from .backend import RemoteDenseBackendError, build_dense_result
from .capabilities import remote_dense_capabilities
from .generator import RemoteDenseGenerationError, bundle_manifest, write_submission_bundle


@dataclass(frozen=True)
class RemoteDenseSettings:
    repo_root: Path
    callback_timeout_sec: float = 30
    backend: str = "auto"
    colmap_command: str | None = None
    gaussian_command: str | None = None
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
        gaussian_command=environ.get("DREAMNAV_REMOTE_GAUSSIAN_COMMAND") or _default_gaussian_command(),
        dense_command=environ.get("DREAMNAV_REMOTE_DENSE_COMMAND") or _default_dense_command(),
        allow_mock_fallback=environ.get("DREAMNAV_REMOTE_DENSE_ALLOW_MOCK_FALLBACK", "1") != "0",
        retained_job_count=max(1, int(environ.get("DREAMNAV_REMOTE_DENSE_RETAINED_JOBS", "8"))),
    )


def create_app(settings: RemoteDenseSettings | None = None) -> FastAPI:
    resolved_settings = settings or default_settings()
    app = FastAPI(title="DreamNav Remote Dense Worker", version="0.1.0")
    app.state.settings = resolved_settings
    app.state.callback_sender = _post_dense_callback
    app.state.job_semaphore = Semaphore(1)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "dreamnav-remote-dense"}

    @app.get("/capabilities")
    def capabilities() -> dict[str, object]:
        return remote_dense_capabilities(resolved_settings)

    @app.get("/jobs/{remote_job_id}")
    def job_status(remote_job_id: str) -> dict[str, object]:
        result_path = resolved_settings.submissions_root / remote_job_id / "result.json"
        if not result_path.is_file():
            raise HTTPException(status_code=404, detail="Remote dense job not found")

        return loads(result_path.read_text(encoding="utf-8"))

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
        except RemoteDenseGenerationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        _write_job_result_metadata(
            submission_bundle.parent,
            manifest,
            status="submitted",
            backend=resolved_settings.backend,
            warnings=[],
            error=None,
        )
        background_tasks.add_task(
            _process_submission,
            submission_bundle,
            submission_bundle.parent,
            manifest,
            callback_url,
            callback_token,
            remote_job_id,
            resolved_settings,
            app.state.callback_sender,
            app.state.job_semaphore,
        )

        return _submission_response(
            job_id=job_id,
            remote_job_id=remote_job_id,
            submission_status="submitted",
            source_video=source_video,
            bundle_file=submission_bundle.name,
            bundle_size_bytes=submission_bundle.stat().st_size,
            frame_count=manifest.get("frame_count", 0),
            backend=resolved_settings.backend,
            warnings=[],
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


def _process_submission(
    submission_bundle: Path,
    job_root: Path,
    manifest: dict[str, object],
    callback_url: str,
    callback_token: str,
    remote_job_id: str,
    settings: RemoteDenseSettings,
    callback_sender,
    job_semaphore: Semaphore,
) -> None:
    try:
        with job_semaphore:
            _write_job_result_metadata(
                job_root,
                manifest,
                status="running",
                backend=settings.backend,
                warnings=[],
                error=None,
            )
            dense_result = build_dense_result(
                submission_bundle,
                job_root,
                settings.backend,
                settings.colmap_command,
                settings.gaussian_command,
                settings.dense_command,
                settings.allow_mock_fallback,
            )
            callback_sender(
                callback_url,
                callback_token,
                dense_result.dense_ply,
                remote_job_id,
                dense_result.backend,
                settings.callback_timeout_sec,
            )
    except Exception as error:
        _write_job_result_metadata(
            job_root,
            manifest,
            status="failed",
            backend=settings.backend,
            warnings=[],
            error=str(error),
        )
        return

    _write_job_result_metadata(
        job_root,
        manifest,
        status="completed",
        backend=dense_result.backend,
        warnings=dense_result.warnings,
        error=None,
    )


def _write_job_result_metadata(
    job_root: Path,
    manifest: dict[str, object],
    status: str,
    backend: str | None,
    warnings: list[str],
    error: str | None,
) -> None:
    payload = {
        "job_id": manifest.get("job_id"),
        "source_video": manifest.get("source_video"),
        "frame_count": manifest.get("frame_count"),
        "status": status,
        "backend": backend,
        "warnings": warnings,
        "error": error,
    }
    (job_root / "result.json").write_text(dumps(payload, indent=2), encoding="utf-8")


def _default_dense_command() -> str | None:
    if environ.get("DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE"):
        docker_adapter = Path(__file__).with_name("docker_command_adapter.py")
        if docker_adapter.is_file():
            return str(docker_adapter)

    adapter_path = Path(__file__).with_name("colmap_command_adapter.py")
    return str(adapter_path) if adapter_path.is_file() else None


def _default_gaussian_command() -> str | None:
    if not (
        environ.get("DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE")
        or environ.get("DREAMNAV_TRAINED_GAUSSIAN_TRAIN_COMMAND_JSON")
        or environ.get("DREAMNAV_TRAINED_GAUSSIAN_EXPORT_COMMAND_JSON")
    ):
        return None

    adapter_path = Path(__file__).with_name("gaussian_command_adapter.py")
    return str(adapter_path) if adapter_path.is_file() else None


app = create_app()
