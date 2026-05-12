from threading import Thread

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from .jobs import JobArtifactNameError, JobArtifactNotFoundError, JobDataError, JobNotFoundError, JobRepository
from .gaussian_import_validation import evaluate_imported_scene
from .repository import SceneDataError, SceneNotFoundError, SceneRepository
from .reconstruction_capabilities import detect_reconstruction_capabilities
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
    SceneAssetStatus,
    SceneAssets,
    UploadResponse,
)
from .splat_assets import SplatAssetError, import_job_splat_asset
from .viewer_assets import ViewerAssetBuildError, build_job_viewer_assets

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

    previous_gaussian_scene = _optional_job_artifact(job_repository, job_id, "gaussian_scene.json")
    previous_visibility = _optional_job_artifact(job_repository, job_id, "visibility_manifest.json")
    previous_quality = _optional_job_artifact(job_repository, job_id, "quality.json")
    payload = await file.read()
    try:
        imported = import_job_splat_asset(
            job_repository.artifact_root(job_id),
            file.filename or "gaussian_input.ply",
            payload,
        )
    except SplatAssetError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    source_video = _job_source_video(job_id, job_repository)
    job_repository.write_artifact(
        job_id,
        "gaussian_scene.json",
        {
            "job_id": job_id,
            "source_video": source_video,
            "backend": "import",
            "command_mode": "imported",
            "splat_file": "splat.ply",
            "gaussian_count": imported.gaussian_count,
            "splat_source": "imported",
            "splat_file_size_bytes": (job_repository.artifact_root(job_id) / "splat.ply").stat().st_size,
            "import_format": imported.import_format,
            "import_file": imported.source_file,
        },
    )
    job_repository.write_artifact(
        job_id,
        "gaussian_import.json",
        {
            "job_id": job_id,
            "source_file": imported.source_file,
            "import_format": imported.import_format,
            "gaussian_count": imported.gaussian_count,
            "file_size_bytes": imported.file_size_bytes,
        },
    )
    try:
        explorer_bundle = build_job_viewer_assets(
            job_id,
            source_video,
            job_repository.artifact_root(job_id),
        )
    except ViewerAssetBuildError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    job_repository.write_artifact(job_id, "explorer_bundle.json", explorer_bundle)
    current_gaussian_scene = job_repository.read_artifact(job_id, "gaussian_scene.json")
    current_visibility = job_repository.read_artifact(job_id, "visibility_manifest.json")
    current_quality = job_repository.read_artifact(job_id, "quality.json")
    featured_candidate = job_repository.featured_scene_ready(job_id)
    import_review = evaluate_imported_scene(
        previous_gaussian_scene,
        previous_visibility,
        previous_quality,
        current_gaussian_scene,
        current_visibility,
        current_quality,
        explorer_bundle["viewer_render_mode"],
        featured_candidate,
    )

    return GaussianImportResponse(
        job_id=job_id,
        source_file=imported.source_file,
        import_format=imported.import_format,
        previous_gaussian_count=import_review["previous_gaussian_count"],
        previous_observed_ratio=import_review["previous_observed_ratio"],
        previous_completion_candidate_ratio=import_review["previous_completion_candidate_ratio"],
        previous_quality_gate=import_review["previous_quality_gate"],
        gaussian_count=imported.gaussian_count,
        file_size_bytes=imported.file_size_bytes,
        observed_ratio=import_review["observed_ratio"],
        completion_candidate_ratio=import_review["completion_candidate_ratio"],
        quality_gate=str(import_review["quality_gate"]),
        viewer_render_mode=explorer_bundle["viewer_render_mode"],
        featured_candidate=featured_candidate,
        validation_status=import_review["validation_status"],
        blockers=import_review["blockers"],
        warnings=import_review["warnings"],
    )


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


def _job_source_video(job_id: str, job_repository: JobRepository) -> str:
    try:
        metadata = job_repository.read_artifact(job_id, "metadata.json")
    except JobArtifactNotFoundError:
        return "imported_gaussian"

    input_video = metadata.get("input_video")
    return input_video if isinstance(input_video, str) and input_video else "imported_gaussian"


def _optional_job_artifact(job_repository: JobRepository, job_id: str, artifact_name: str) -> dict[str, object] | None:
    try:
        return job_repository.read_artifact(job_id, artifact_name)
    except JobArtifactNotFoundError:
        return None


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
