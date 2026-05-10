from threading import Thread

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from .jobs import JobDataError, JobNotFoundError, JobRepository
from .repository import SceneDataError, SceneNotFoundError, SceneRepository
from .schemas import (
    DemoScene,
    HealthResponse,
    JobStatus,
    QualityReport,
    SceneAssetStatus,
    SceneAssets,
    UploadResponse,
)

router = APIRouter()


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
        Thread(target=request.app.state.processing_worker.process_next_job, daemon=True).start()

    return response


@router.get("/status/{job_id}", response_model=JobStatus)
def job_status(job_id: str, request: Request) -> JobStatus:
    return _job_repository(request).get_status(job_id)


def _repository(request: Request) -> SceneRepository:
    return request.app.state.scene_repository


def _job_repository(request: Request) -> JobRepository:
    return request.app.state.job_repository


def map_scene_errors(error: Exception) -> HTTPException:
    if isinstance(error, SceneNotFoundError):
        return HTTPException(status_code=404, detail="Scene not found")

    if isinstance(error, SceneDataError):
        return HTTPException(status_code=500, detail="Scene data invalid")

    return HTTPException(status_code=500, detail="Unexpected API error")


def map_job_errors(error: Exception) -> HTTPException:
    if isinstance(error, JobNotFoundError):
        return HTTPException(status_code=404, detail="Job not found")

    if isinstance(error, JobDataError):
        return HTTPException(status_code=500, detail="Job data invalid")

    return HTTPException(status_code=500, detail="Unexpected API error")
