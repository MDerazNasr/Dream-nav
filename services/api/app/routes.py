from threading import Thread

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from .jobs import JobArtifactNameError, JobArtifactNotFoundError, JobDataError, JobNotFoundError, JobRepository
from .repository import SceneDataError, SceneNotFoundError, SceneRepository
from .schemas import (
    DemoScene,
    HealthResponse,
    JobArtifact,
    JobSceneBundle,
    JobStatus,
    QualityReport,
    SceneAssetStatus,
    SceneAssets,
    UploadResponse,
)

router = APIRouter()

VIEWER_ASSET_NAMES = {
    "camera_path.json",
    "completion_manifest.json",
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

    camera_path_artifact = "camera_path.json"
    metadata = job_repository.read_artifact(job_id, "metadata.json")
    quality_report = job_repository.read_artifact(job_id, "quality.json")
    camera_path = job_repository.read_artifact(job_id, camera_path_artifact)
    visibility = job_repository.read_artifact(job_id, "visibility_manifest.json")
    completion = job_repository.read_artifact(job_id, "completion_manifest.json")
    asset_status = _job_asset_status(job_id, status.output_scene_id, job_repository)

    return JobSceneBundle(
        job_id=job_id,
        output_scene_id=status.output_scene_id,
        assets=SceneAssets(
            scene_id=status.output_scene_id,
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
