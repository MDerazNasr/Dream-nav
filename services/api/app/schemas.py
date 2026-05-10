from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DemoScene(StrictModel):
    scene_id: str
    title: str
    thumbnail_url: str
    description: str


class SceneAssets(StrictModel):
    scene_id: str
    splat_url: str
    metadata_url: str
    visibility_manifest_url: str
    completion_manifest_url: str
    quality_report_url: str


class SceneAssetStatus(StrictModel):
    scene_id: str
    splat_url: str
    splat_available: bool
    viewer_render_mode: str
    missing_assets: list[str]


class UploadResponse(StrictModel):
    job_id: str
    validation_status: str
    warnings: list[str]
    estimated_processing_time_sec: int = Field(ge=0)


class JobStatus(StrictModel):
    job_id: str
    state: str
    stage: str
    progress: float = Field(ge=0, le=1)
    elapsed_sec: int = Field(ge=0)
    message: str
    output_scene_id: str | None
    error_message: str | None
    failed_stage: str | None
    failed_artifact: str | None


class JobArtifact(StrictModel):
    job_id: str
    artifact_name: str
    payload: dict[str, Any]


class QualityReport(StrictModel):
    scene_id: str
    pose_backend: str
    frame_count: int = Field(ge=0)
    visibility_threshold_observed: int = Field(ge=1)
    splat_fps: float = Field(ge=0)
    scene_model_training_sec: float = Field(ge=0)
    heldout_psnr_median: float | None
    quality_gate: str
    completion_latency_ms_p50: float | None
    completion_latency_ms_p95: float | None
    runtime_path: str
    cached_completion: bool


class VisibilitySummary(StrictModel):
    observed_threshold: int = Field(ge=1)
    partial_threshold: tuple[int, int]
    observed_ratio: float = Field(ge=0, le=1)
    partial_ratio: float = Field(ge=0, le=1)
    completion_candidate_ratio: float = Field(ge=0, le=1)


class SceneModelSummary(StrictModel):
    enabled: bool
    architecture: str
    train_views: int = Field(ge=0)
    heldout_views: int = Field(ge=0)
    training_time_sec: float = Field(ge=0)
    loss: str
    heldout_psnr_median: float | None
    quality_gate: str
    lpips: float | None


class OptimizationSummary(StrictModel):
    fp32_latency_ms_p50: float | None
    fp16_latency_ms_p50: float | None
    compiled_latency_ms_p50: float | None
    tensorrt_latency_ms_p50: float | None
    cached_output_latency_ms_p50: float | None


class ZoneAssets(StrictModel):
    observed: str
    partial: str
    completion: str
    unknown: str


class CaptureQuality(StrictModel):
    capture_score: float = Field(ge=0, le=1)
    sharpness_score: float = Field(ge=0, le=1)
    parallax_score: float = Field(ge=0, le=1)
    texture_score: float = Field(ge=0, le=1)
    splat_fps: float = Field(ge=0)
    processing_time_sec: float = Field(ge=0)


class ProductTools(StrictModel):
    lens_modes: list[str]
    camera_markers_enabled: bool
    notes_enabled: bool


class SceneMetadata(StrictModel):
    scene_id: str
    title: str
    input_video: str
    duration_sec: float = Field(ge=0)
    frame_count: int = Field(ge=0)
    pose_backend: str
    camera_path: str
    splat_file: str
    visibility: VisibilitySummary
    scene_model: SceneModelSummary
    optimization: OptimizationSummary
    zones: ZoneAssets
    quality: CaptureQuality
    product_tools: ProductTools


class HealthResponse(StrictModel):
    status: str
    service: str
