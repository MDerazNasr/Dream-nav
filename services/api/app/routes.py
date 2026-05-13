from threading import Thread

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from .gaussian_imports import GaussianImportError, apply_imported_gaussian_asset
from .jobs import JobArtifactNameError, JobArtifactNotFoundError, JobDataError, JobNotFoundError, JobRepository
from .repository import SceneDataError, SceneNotFoundError, SceneRepository
from .reconstruction_capabilities import detect_reconstruction_capabilities
from .remote_dense_handoff import (
    RemoteDenseHandoffError,
    build_remote_dense_bundle,
    callback_warnings,
    remote_submission_payload,
    submit_remote_dense_job,
)
from .schemas import (
    DemoScene,
    DemoReadiness,
    GaussianImportResponse,
    HealthResponse,
    JobArtifact,
    JobSceneBundle,
    JobStatus,
    QualityReport,
    ReconstructionCapabilities,
    RemoteDenseSubmissionResponse,
    SceneAssetStatus,
    SceneAssets,
    UploadResponse,
)

router = APIRouter()

VIEWER_ASSET_NAMES = {
    "camera_path.json",
    "completion_manifest.json",
    "completion/baseline_nearest_001.png",
    "completion/baseline_nearest_001.svg",
    "completion/pred_001.svg",
    "completion/pred_001_mask.svg",
    "completion_zone.json",
    "metadata.json",
    "observed_zone.json",
    "partial_zone.json",
    "quality.json",
    "splat.ply",
    "unknown_zone.json",
    "visibility_manifest.json",
}


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="dreamnav-api")


@router.get("/demo-scenes", response_model=list[DemoScene])
def demo_scenes(request: Request) -> list[DemoScene]:
    return _repository(request).list_demo_scenes()


@router.get("/reconstruction-capabilities", response_model=ReconstructionCapabilities)
def reconstruction_capabilities(request: Request) -> ReconstructionCapabilities:
    return detect_reconstruction_capabilities(request.app.state.settings.processing)


@router.get("/demo-readiness/{scene_id}", response_model=DemoReadiness)
def demo_readiness(scene_id: str, request: Request) -> DemoReadiness:
    return _repository(request).get_demo_readiness(scene_id)


@router.get("/scene/{scene_id}", response_model=SceneAssets)
def scene_assets(scene_id: str, request: Request) -> SceneAssets:
    repo = _repository(request)

    if not repo.scene_exists(scene_id):
        raise HTTPException(status_code=404, detail="Scene not found")

    return SceneAssets(
        scene_id=scene_id,
        splat_url=f"/scenes/{scene_id}/splat.ply",
        metadata_url=f"/scenes/{scene_id}/metadata.json",
        visibility_manifest_url=f"/scenes/{scene_id}/visibility_manifest.json",
        completion_manifest_url=f"/scenes/{scene_id}/completion_manifest.json",
        quality_report_url=f"/scenes/{scene_id}/quality.json",
    )


@router.get("/quality/{scene_id}", response_model=QualityReport)
def quality(scene_id: str, request: Request) -> QualityReport:
    return _repository(request).get_quality_report(scene_id)


@router.get("/scene/{scene_id}/asset-status", response_model=SceneAssetStatus)
def scene_asset_status(scene_id: str, request: Request) -> SceneAssetStatus:
    return _repository(request).get_asset_status(scene_id)


@router.post("/upload", response_model=UploadResponse)
async def upload_walkthrough(
    request: Request,
    file: UploadFile = File(...),
) -> UploadResponse:
    response = await _job_repository(request).create_upload_job(file)

    if request.app.state.auto_start_worker:
        Thread(target=request.app.state.processing_worker.process_available_jobs, daemon=True).start()

    return response


@router.post("/jobs/{job_id}/import-gaussian", response_model=GaussianImportResponse)
async def import_gaussian_asset(
    job_id: str,
    request: Request,
    file: UploadFile = File(...),
) -> GaussianImportResponse:
    job_repository = _job_repository(request)
    status = job_repository.get_status(job_id)
    if status.state != "completed":
        raise HTTPException(status_code=409, detail="Job scene bundle is not ready for Gaussian import")

    payload = await file.read()
    try:
        return apply_imported_gaussian_asset(
            job_repository,
            job_id,
            file.filename or "gaussian_input.ply",
            payload,
        )
    except GaussianImportError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

@router.post("/jobs/{job_id}/submit-remote-dense", response_model=RemoteDenseSubmissionResponse)
def submit_remote_dense(job_id: str, request: Request) -> RemoteDenseSubmissionResponse:
    job_repository = _job_repository(request)
    status = job_repository.get_status(job_id)
    if status.state != "completed":
        raise HTTPException(status_code=409, detail="Job scene bundle is not ready for remote dense submission")

    settings = request.app.state.settings
    if not settings.remote_dense_url:
        raise HTTPException(status_code=409, detail="Remote dense backend is not configured")

    if not settings.remote_dense_callback_token:
        raise HTTPException(status_code=409, detail="Remote dense callback token is not configured")

    callback_url = _remote_dense_callback_url(request, job_id)
    warnings = callback_warnings(settings.public_api_base_url)
    try:
        job = job_repository.get_job(job_id)
        bundle = build_remote_dense_bundle(
            job_id,
            job_repository.upload_path(job),
            job_repository.artifact_root(job_id),
            callback_url,
            settings.remote_dense_callback_token,
        )
        submission = submit_remote_dense_job(
            settings.remote_dense_url,
            bundle,
            settings.remote_dense_callback_token,
            provider_token=settings.remote_dense_token,
        )
    except RemoteDenseHandoffError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    payload = remote_submission_payload(
        job_id,
        submission,
        callback_token_configured=True,
    )
    payload["warnings"] = [*warnings, *submission.warnings]
    job_repository.write_artifact(job_id, "remote_dense_submission.json", payload)
    return RemoteDenseSubmissionResponse(**{key: value for key, value in payload.items() if key != "submitted_at_sec"})


@router.post("/jobs/{job_id}/remote-dense-result", response_model=GaussianImportResponse)
async def remote_dense_result(
    job_id: str,
    request: Request,
    file: UploadFile = File(...),
    x_dreamnav_callback_token: str | None = Header(default=None),
    x_dreamnav_remote_backend: str | None = Header(default=None),
    x_dreamnav_remote_job_id: str | None = Header(default=None),
) -> GaussianImportResponse:
    settings = request.app.state.settings
    if settings.remote_dense_callback_token and x_dreamnav_callback_token != settings.remote_dense_callback_token:
        raise HTTPException(status_code=403, detail="Remote dense callback token is invalid")

    job_repository = _job_repository(request)
    status = job_repository.get_status(job_id)
    if status.state != "completed":
        raise HTTPException(status_code=409, detail="Job scene bundle is not ready for Gaussian import")

    payload = await file.read()
    try:
        response = apply_imported_gaussian_asset(
            job_repository,
            job_id,
            file.filename or "remote_dense_result.ply",
            payload,
        )
    except GaussianImportError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    job_repository.write_artifact(
        job_id,
        "remote_dense_result.json",
        {
            "job_id": job_id,
            "remote_job_id": x_dreamnav_remote_job_id,
            "backend": x_dreamnav_remote_backend,
            "source_file": response.source_file,
            "validation_status": response.validation_status,
            "gaussian_count": response.gaussian_count,
        },
    )
    return response


@router.get("/status/{job_id}", response_model=JobStatus)
def job_status(job_id: str, request: Request) -> JobStatus:
    return _job_repository(request).get_status(job_id)


@router.get("/jobs/{job_id}/artifacts/{artifact_name:path}", response_model=JobArtifact)
def job_artifact(job_id: str, artifact_name: str, request: Request) -> JobArtifact:
    payload = _job_repository(request).read_artifact(job_id, artifact_name)
    return JobArtifact(job_id=job_id, artifact_name=artifact_name, payload=payload)


@router.get("/jobs/{job_id}/scene-bundle", response_model=JobSceneBundle)
def job_scene_bundle(job_id: str, request: Request) -> JobSceneBundle:
    job_repository = _job_repository(request)
    status = job_repository.get_status(job_id)

    if status.state != "completed" or status.output_scene_id is None:
        raise HTTPException(status_code=409, detail="Job explorer bundle is not ready")

    return _build_job_scene_bundle(job_id, status.output_scene_id, job_repository)


@router.get("/featured-job-scene-bundle", response_model=JobSceneBundle)
def featured_job_scene_bundle(request: Request) -> JobSceneBundle:
    job_repository = _job_repository(request)
    job_id = job_repository.latest_completed_job_id()
    if job_id is None:
        raise HTTPException(status_code=404, detail="Featured job scene is not available")

    status = job_repository.get_status(job_id)
    if status.output_scene_id is None:
        raise HTTPException(status_code=404, detail="Featured job scene is not available")

    return _build_job_scene_bundle(job_id, status.output_scene_id, job_repository)


@router.get("/jobs/{job_id}/viewer-assets/{asset_name:path}")
def job_viewer_asset(job_id: str, asset_name: str, request: Request) -> FileResponse:
    job_repository = _job_repository(request)
    job_repository.get_status(job_id)
    if asset_name not in VIEWER_ASSET_NAMES:
        raise HTTPException(status_code=400, detail="Unsafe viewer asset name")

    asset_path = job_repository.artifact_root(job_id) / asset_name
    if not asset_path.is_file():
        raise HTTPException(status_code=404, detail="Viewer asset not found")

    return FileResponse(asset_path)


def _repository(request: Request) -> SceneRepository:
    return request.app.state.scene_repository


def _job_repository(request: Request) -> JobRepository:
    return request.app.state.job_repository


def _job_asset_status(job_id: str, scene_id: str, job_repository: JobRepository) -> SceneAssetStatus:
    splat_path = job_repository.artifact_root(job_id) / "splat.ply"
    splat_available = splat_path.is_file()
    return SceneAssetStatus(
        scene_id=scene_id,
        splat_url=f"/jobs/{job_id}/viewer-assets/splat.ply",
        splat_available=splat_available,
        viewer_render_mode="splat" if splat_available else "placeholder",
        missing_assets=[] if splat_available else ["splat.ply"],
    )


def _build_job_scene_bundle(job_id: str, output_scene_id: str, job_repository: JobRepository) -> JobSceneBundle:
    camera_path_artifact = "camera_path.json"
    metadata = job_repository.read_artifact(job_id, "metadata.json")
    quality_report = job_repository.read_artifact(job_id, "quality.json")
    camera_path = job_repository.read_artifact(job_id, camera_path_artifact)
    visibility = job_repository.read_artifact(job_id, "visibility_manifest.json")
    completion = job_repository.read_artifact(job_id, "completion_manifest.json")
    asset_status = _job_asset_status(job_id, output_scene_id, job_repository)

    return JobSceneBundle(
        job_id=job_id,
        output_scene_id=output_scene_id,
        assets=SceneAssets(
            scene_id=output_scene_id,
            splat_url=f"/jobs/{job_id}/viewer-assets/splat.ply",
            metadata_url=f"/jobs/{job_id}/viewer-assets/metadata.json",
            visibility_manifest_url=f"/jobs/{job_id}/viewer-assets/visibility_manifest.json",
            completion_manifest_url=f"/jobs/{job_id}/viewer-assets/completion_manifest.json",
            quality_report_url=f"/jobs/{job_id}/viewer-assets/quality.json",
        ),
        metadata=metadata,
        quality=quality_report,
        camera_path_artifact=camera_path_artifact,
        camera_path=camera_path,
        visibility=visibility,
        completion=completion,
        asset_status=asset_status,
    )


def map_scene_errors(error: Exception) -> HTTPException:
    if isinstance(error, SceneNotFoundError):
        return HTTPException(status_code=404, detail="Scene not found")

    if isinstance(error, SceneDataError):
        return HTTPException(status_code=500, detail="Scene data invalid")

    return HTTPException(status_code=500, detail="Unexpected API error")


def map_job_errors(error: Exception) -> HTTPException:
    if isinstance(error, JobNotFoundError):
        return HTTPException(status_code=404, detail="Job not found")

    if isinstance(error, JobArtifactNotFoundError):
        return HTTPException(status_code=404, detail="Job artifact not found")

    if isinstance(error, JobArtifactNameError):
        return HTTPException(status_code=400, detail="Unsafe artifact name")

    if isinstance(error, JobDataError):
        return HTTPException(status_code=500, detail="Job data invalid")

    return HTTPException(status_code=500, detail="Unexpected API error")


def _remote_dense_callback_url(request: Request, job_id: str) -> str:
    configured_base_url = request.app.state.settings.public_api_base_url
    base_url = configured_base_url or str(request.base_url).rstrip("/")
    return f"{base_url}/jobs/{job_id}/remote-dense-result"
