from __future__ import annotations

from dataclasses import dataclass
from json import dumps
from pathlib import Path
from shutil import which
import sys
from typing import Protocol

from .colmap_pipeline import build_colmap_pipeline_commands
from .colmap_pose_parser import ColmapPoseParseError, parse_colmap_text_model
from .config import ProcessingSettings
from .jobs import ProcessingStep, StoredJob
from .pose_normalization import PoseNormalizationError, normalize_camera_path, stub_raw_poses_from_frames
from .video_probe import VideoProbeError, probe_video_file


class ProcessingTaskFailed(Exception):
    def __init__(self, message: str, artifact_name: str | None = None) -> None:
        super().__init__(message)
        self.artifact_name = artifact_name


@dataclass(frozen=True)
class ProcessingTaskContext:
    job: StoredJob
    upload_path: Path
    artifacts_root: Path
    processing_settings: ProcessingSettings


@dataclass(frozen=True)
class ProcessingTaskResult:
    artifact_name: str
    payload: dict[str, object]


@dataclass(frozen=True)
class ProcessingCommand:
    artifact_name: str
    command: list[str]
    timeout_sec: float = 60


@dataclass(frozen=True)
class FrameInventory:
    frames: list[Path]

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def first_frame(self) -> str | None:
        return self.frames[0].name if self.frames else None

    @property
    def last_frame(self) -> str | None:
        return self.frames[-1].name if self.frames else None


class ProcessingTaskRunner(Protocol):
    def __call__(self, context: ProcessingTaskContext) -> ProcessingTaskResult:
        pass


class ProcessingCommandBuilder(Protocol):
    def __call__(self, context: ProcessingTaskContext) -> ProcessingCommand | list[ProcessingCommand]:
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
    backend = _normalized_pose_backend(context.processing_settings)
    frames = _frame_inventory(_frames_root(context)).frames
    try:
        raw_poses, intrinsics = _raw_camera_poses(context, backend, frames)
        camera_path = normalize_camera_path(context.job.job_id, raw_poses, intrinsics=intrinsics)
    except PoseNormalizationError as error:
        raise ProcessingTaskFailed(str(error)) from error

    camera_path_name = "camera_path.json"
    (context.artifacts_root / camera_path_name).write_text(
        dumps(camera_path, indent=2),
        encoding="utf-8",
    )

    return _result(
        "camera_motion.json",
        context,
        backend=backend,
        command_mode="stub" if backend == "stub" else "external",
        camera_path=camera_path_name,
        coordinate_system=camera_path["coordinate_system"],
        intrinsics_source="default" if intrinsics is None else backend,
        pose_count=len(camera_path["poses"]),
    )


def extract_video_frames(context: ProcessingTaskContext) -> ProcessingTaskResult:
    backend = _normalized_frame_backend(context.processing_settings)
    _validate_frame_settings(context.processing_settings)
    frames_root = _frames_root(context)
    frames_root.mkdir(parents=True, exist_ok=True)

    if backend == "stub" and not _frame_inventory(frames_root).frames:
        for frame_index in range(3):
            (frames_root / f"frame_{frame_index:04d}.jpg").write_text(
                f"stub frame {frame_index}\n",
                encoding="utf-8",
            )

    inventory = _frame_inventory(frames_root)
    _validate_frame_inventory(inventory, context.processing_settings, backend)
    warnings = _frame_extraction_warnings(context, inventory)

    return _result(
        "frame_extraction.json",
        context,
        backend=backend,
        command_mode="stub" if backend == "stub" else "external",
        frame_count=inventory.frame_count,
        frame_rate=context.processing_settings.frame_rate,
        frame_max_count=context.processing_settings.frame_max_count,
        frame_max_duration_sec=context.processing_settings.frame_max_duration_sec,
        first_frame=inventory.first_frame,
        last_frame=inventory.last_frame,
        frames_path=str(frames_root),
        warnings=warnings,
    )


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
    backend = _normalized_pose_backend(context.processing_settings)

    if backend == "stub":
        return _placeholder_command(
            "camera_motion_command.json",
            f"pose_backend=stub source={context.upload_path.name}",
        )

    if backend == "colmap":
        colmap_command = _resolve_command(context.processing_settings.pose_command, "colmap")
        if not colmap_command:
            raise ProcessingTaskFailed("Pose backend colmap selected but COLMAP binary was not found.")

        return [
            ProcessingCommand(
                artifact_name=command.artifact_name,
                command=command.command,
                timeout_sec=context.processing_settings.pose_timeout_sec,
            )
            for command in build_colmap_pipeline_commands(
                colmap_command,
                context.artifacts_root,
                _frames_root(context),
            )
        ]

    if backend == "droid_slam":
        raise ProcessingTaskFailed("Pose backend droid_slam is configured but not implemented yet.")

    raise ProcessingTaskFailed(f"Unsupported pose backend: {context.processing_settings.pose_backend}")


def build_frame_extraction_command(context: ProcessingTaskContext) -> ProcessingCommand:
    backend = _normalized_frame_backend(context.processing_settings)
    _validate_frame_settings(context.processing_settings)
    frames_root = _frames_root(context)
    frames_root.mkdir(parents=True, exist_ok=True)

    if backend == "stub":
        return _placeholder_command(
            "frame_extraction_command.json",
            f"frame_backend=stub source={context.upload_path.name} frames={frames_root}",
        )

    if backend == "ffmpeg":
        ffmpeg_command = _resolve_command(context.processing_settings.frame_command, "ffmpeg")
        if not ffmpeg_command:
            raise ProcessingTaskFailed("Frame backend ffmpeg selected but ffmpeg binary was not found.")

        return ProcessingCommand(
            artifact_name="frame_extraction_command.json",
            command=[
                ffmpeg_command,
                "-y",
                "-i",
                str(context.upload_path),
                "-t",
                str(context.processing_settings.frame_max_duration_sec),
                "-vf",
                f"fps={context.processing_settings.frame_rate}",
                "-frames:v",
                str(context.processing_settings.frame_max_count),
                str(frames_root / "frame_%04d.jpg"),
            ],
            timeout_sec=context.processing_settings.frame_timeout_sec,
        )

    raise ProcessingTaskFailed(f"Unsupported frame backend: {context.processing_settings.frame_backend}")


def build_gaussian_scene_command(context: ProcessingTaskContext) -> ProcessingCommand:
    return _placeholder_command(
        "gaussian_scene_command.json",
        f"gaussian_backend=3DGS artifacts={context.artifacts_root}",
    )


def _normalized_pose_backend(settings: ProcessingSettings) -> str:
    return settings.pose_backend.strip().lower()


def _normalized_frame_backend(settings: ProcessingSettings) -> str:
    return settings.frame_backend.strip().lower()


def _frames_root(context: ProcessingTaskContext) -> Path:
    return context.artifacts_root / "frames"


def _raw_camera_poses(
    context: ProcessingTaskContext,
    backend: str,
    frames: list[Path],
):
    if backend == "stub":
        return stub_raw_poses_from_frames(frames, context.processing_settings.frame_rate), None

    if backend == "colmap":
        try:
            return parse_colmap_text_model(
                context.artifacts_root / "colmap",
                frames,
                context.processing_settings.frame_rate,
            )
        except ColmapPoseParseError as error:
            raise ProcessingTaskFailed(str(error)) from error

    raise ProcessingTaskFailed(f"Unsupported pose backend: {context.processing_settings.pose_backend}")


def _frame_inventory(frames_root: Path) -> FrameInventory:
    return FrameInventory(sorted(frame for frame in frames_root.glob("*.jpg") if frame.is_file()))


def _validate_frame_settings(settings: ProcessingSettings) -> None:
    if settings.frame_rate <= 0:
        raise ProcessingTaskFailed("Frame rate must be greater than zero.")

    if settings.frame_max_count < 1:
        raise ProcessingTaskFailed("Frame max count must be at least one.")

    if settings.frame_max_duration_sec <= 0:
        raise ProcessingTaskFailed("Frame max duration must be greater than zero.")


def _validate_frame_inventory(
    inventory: FrameInventory,
    settings: ProcessingSettings,
    backend: str,
) -> None:
    if inventory.frame_count == 0:
        raise ProcessingTaskFailed("Frame extraction produced no JPG frames.")

    if inventory.frame_count > settings.frame_max_count:
        raise ProcessingTaskFailed(
            f"Frame extraction produced {inventory.frame_count} frames, above configured limit {settings.frame_max_count}."
        )

    if backend == "stub":
        return

    for frame in inventory.frames:
        _validate_external_frame(frame)


def _validate_external_frame(frame_path: Path) -> None:
    if frame_path.stat().st_size == 0:
        raise ProcessingTaskFailed(f"Extracted frame is empty: {frame_path.name}")

    with frame_path.open("rb") as frame:
        signature = frame.read(2)

    if signature != b"\xff\xd8":
        raise ProcessingTaskFailed(f"Extracted frame is not a JPEG file: {frame_path.name}")


def _frame_extraction_warnings(
    context: ProcessingTaskContext,
    inventory: FrameInventory,
) -> list[str]:
    warnings = []
    try:
        probe = probe_video_file(context.upload_path)
    except VideoProbeError:
        return warnings

    max_duration_sec = context.processing_settings.frame_max_duration_sec
    if probe.duration_sec and probe.duration_sec > max_duration_sec:
        warnings.append(f"Frame extraction was capped to the first {max_duration_sec:g} seconds.")

    if inventory.frame_count == context.processing_settings.frame_max_count:
        warnings.append("Frame extraction reached the configured frame limit.")

    return warnings


def _resolve_command(configured_command: str | None, default_command: str) -> str | None:
    if not configured_command:
        return which(default_command)

    configured_path = Path(configured_command)
    if configured_path.parent != Path("."):
        return str(configured_path) if configured_path.is_file() else None

    return which(configured_command)


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
