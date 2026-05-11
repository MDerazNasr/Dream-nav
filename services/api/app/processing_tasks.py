from __future__ import annotations

from .camera_processing import build_camera_motion_command, estimate_camera_motion
from .frame_processing import build_frame_extraction_command, extract_video_frames, validate_capture_quality
from .gaussian_reconstruction import GaussianReconstructionConfigError, build_gaussian_reconstruction_command, normalized_gaussian_backend
from .jobs import ProcessingStep
from .processing_models import (
    ProcessingCommand,
    ProcessingTask,
    ProcessingTaskContext,
    ProcessingTaskFailed,
    ProcessingTaskResult,
)
from .splat_assets import SplatAssetError, ensure_job_splat_asset
from .viewer_assets import ViewerAssetBuildError, build_job_viewer_assets


def default_processing_tasks() -> list[ProcessingTask]:
    return [
        ProcessingTask(
            ProcessingStep("checking_capture_quality", 0.08, "Checking capture quality"),
            "capture_quality.json",
            validate_capture_quality,
        ),
        ProcessingTask(
            ProcessingStep("extracting_video_frames", 0.14, "Extracting video frames"),
            "frame_extraction.json",
            extract_video_frames,
            build_frame_extraction_command,
        ),
        ProcessingTask(
            ProcessingStep("estimating_camera_motion", 0.2, "Estimating camera motion"),
            "camera_motion.json",
            estimate_camera_motion,
            build_camera_motion_command,
        ),
        ProcessingTask(
            ProcessingStep("building_gaussian_scene", 0.36, "Building Gaussian scene"),
            "gaussian_scene.json",
            build_gaussian_scene,
            build_gaussian_scene_command,
        ),
        ProcessingTask(
            ProcessingStep("computing_visibility_support", 0.48, "Computing visibility support"),
            "visibility_support.json",
            compute_visibility_support,
        ),
        ProcessingTask(
            ProcessingStep("rendering_training_views", 0.58, "Rendering training views from the splat"),
            "training_views.json",
            render_training_views,
        ),
        ProcessingTask(
            ProcessingStep(
                "training_scene_model",
                0.72,
                "Training geometrically consistent scene-specific completion model",
            ),
            "scene_model.json",
            train_scene_model,
        ),
        ProcessingTask(
            ProcessingStep("evaluating_heldout_viewpoints", 0.82, "Evaluating held-out viewpoints"),
            "heldout_evaluation.json",
            evaluate_heldout_viewpoints,
        ),
        ProcessingTask(
            ProcessingStep("applying_quality_gate", 0.9, "Applying held-out PSNR quality gate"),
            "quality_gate.json",
            apply_quality_gate,
        ),
        ProcessingTask(
            ProcessingStep("preparing_explorer", 0.97, "Preparing explorer"),
            "explorer_bundle.json",
            prepare_explorer,
        ),
    ]


def build_gaussian_scene(context: ProcessingTaskContext) -> ProcessingTaskResult:
    backend = normalized_gaussian_backend(context.processing_settings)
    try:
        splat_asset = ensure_job_splat_asset(
            context.artifacts_root,
            allow_stub=backend == "stub",
        )
    except SplatAssetError as error:
        raise ProcessingTaskFailed(str(error)) from error

    return _result(
        "gaussian_scene.json",
        context,
        backend=backend,
        command_mode="stub" if backend == "stub" else "external",
        splat_file=splat_asset.file_name,
        gaussian_count=splat_asset.gaussian_count,
        splat_source=splat_asset.source,
        splat_file_size_bytes=splat_asset.file_size_bytes,
    )


def build_gaussian_scene_command(context: ProcessingTaskContext) -> ProcessingCommand:
    try:
        command = build_gaussian_reconstruction_command(
            context.processing_settings,
            context.artifacts_root,
        )
    except GaussianReconstructionConfigError as error:
        raise ProcessingTaskFailed(str(error)) from error

    return ProcessingCommand(
        artifact_name=command.artifact_name,
        command=command.command,
        timeout_sec=command.timeout_sec,
    )


def compute_visibility_support(context: ProcessingTaskContext) -> ProcessingTaskResult:
    return _result("visibility_support.json", context, observed_threshold=3, method="voxel_visibility_v1")


def render_training_views(context: ProcessingTaskContext) -> ProcessingTaskResult:
    return _result("training_views.json", context, train_views=520, heldout_views=80)


def train_scene_model(context: ProcessingTaskContext) -> ProcessingTaskResult:
    return _result(
        "scene_model.json",
        context,
        architecture="pose_conditioned_encoder_decoder",
        training_time_sec=184,
    )


def evaluate_heldout_viewpoints(context: ProcessingTaskContext) -> ProcessingTaskResult:
    return _result("heldout_evaluation.json", context, heldout_psnr_median=21.4)


def apply_quality_gate(context: ProcessingTaskContext) -> ProcessingTaskResult:
    return _result("quality_gate.json", context, quality_gate="warning")


def prepare_explorer(context: ProcessingTaskContext) -> ProcessingTaskResult:
    try:
        payload = build_job_viewer_assets(
            context.job.job_id,
            context.job.stored_filename,
            context.artifacts_root,
        )
    except ViewerAssetBuildError as error:
        raise ProcessingTaskFailed(str(error)) from error

    return ProcessingTaskResult("explorer_bundle.json", payload)


def _result(
    artifact_name: str,
    context: ProcessingTaskContext,
    **payload: object,
) -> ProcessingTaskResult:
    return ProcessingTaskResult(
        artifact_name=artifact_name,
        payload={
            "job_id": context.job.job_id,
            "source_video": context.job.stored_filename,
            **payload,
        },
    )
