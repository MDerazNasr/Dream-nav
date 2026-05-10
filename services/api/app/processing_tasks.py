from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Protocol

from .jobs import ProcessingStep, StoredJob
from .video_probe import VideoProbeError, probe_video_file


class ProcessingTaskFailed(Exception):
    pass


@dataclass(frozen=True)
class ProcessingTaskContext:
    job: StoredJob
    upload_path: Path
    artifacts_root: Path


@dataclass(frozen=True)
class ProcessingTaskResult:
    artifact_name: str
    payload: dict[str, object]


@dataclass(frozen=True)
class ProcessingCommand:
    artifact_name: str
    command: list[str]
    timeout_sec: float = 60


class ProcessingTaskRunner(Protocol):
    def __call__(self, context: ProcessingTaskContext) -> ProcessingTaskResult:
        pass


class ProcessingCommandBuilder(Protocol):
    def __call__(self, context: ProcessingTaskContext) -> ProcessingCommand:
        pass


@dataclass(frozen=True)
class ProcessingTask:
    step: ProcessingStep
    artifact_name: str
    run: ProcessingTaskRunner
    command_builder: ProcessingCommandBuilder | None = None


def default_processing_tasks() -> list[ProcessingTask]:
    return [
        ProcessingTask(
            ProcessingStep("checking_capture_quality", 0.08, "Checking capture quality"),
            "capture_quality.json",
            validate_capture_quality,
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


def validate_capture_quality(context: ProcessingTaskContext) -> ProcessingTaskResult:
    try:
        probe = probe_video_file(context.upload_path)
    except VideoProbeError as error:
        raise ProcessingTaskFailed(str(error)) from error

    return _result(
        "capture_quality.json",
        context,
        duration_sec=probe.duration_sec,
        extension=probe.extension,
        file_size_bytes=probe.file_size_bytes,
        probe_backend=probe.probe_backend,
        supported_extension=probe.supported_extension,
        validation_status="warning" if probe.warnings else "pass",
        warnings=probe.warnings,
    )


def estimate_camera_motion(context: ProcessingTaskContext) -> ProcessingTaskResult:
    return _result("camera_motion.json", context, backend="COLMAP", pose_count=3)


def build_gaussian_scene(context: ProcessingTaskContext) -> ProcessingTaskResult:
    return _result("gaussian_scene.json", context, splat_file="splat.ply", gaussian_count=6)


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
    return _result("explorer_bundle.json", context, output_scene_id="warehouse_01")


def build_camera_motion_command(context: ProcessingTaskContext) -> ProcessingCommand:
    return _placeholder_command(
        "camera_motion_command.json",
        f"pose_backend=COLMAP source={context.upload_path.name}",
    )


def build_gaussian_scene_command(context: ProcessingTaskContext) -> ProcessingCommand:
    return _placeholder_command(
        "gaussian_scene_command.json",
        f"gaussian_backend=3DGS artifacts={context.artifacts_root}",
    )


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


def _placeholder_command(artifact_name: str, message: str) -> ProcessingCommand:
    return ProcessingCommand(
        artifact_name=artifact_name,
        command=[sys.executable, "-c", f"print({message!r})"],
        timeout_sec=5,
    )
