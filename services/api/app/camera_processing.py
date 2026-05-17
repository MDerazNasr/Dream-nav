from __future__ import annotations

from json import dumps
from pathlib import Path

from .colmap_pipeline import build_colmap_pipeline_commands
from .colmap_pose_parser import ColmapPoseParseError, parse_colmap_text_model
from .config import ProcessingSettings
from .frame_processing import frame_inventory, frames_root
from .pose_normalization import PoseNormalizationError, normalize_camera_path, stub_raw_poses_from_frames
from .processing_command_utils import placeholder_command, resolve_command
from .processing_models import ProcessingCommand, ProcessingTaskContext, ProcessingTaskFailed, ProcessingTaskResult

COLMAP_MAPPER_MIN_TIMEOUT_SEC = 300
COLMAP_MAPPER_TIMEOUT_PER_FRAME_SEC = 6
COLMAP_MAPPER_MAX_TIMEOUT_SEC = 900


def estimate_camera_motion(context: ProcessingTaskContext) -> ProcessingTaskResult:
    backend = normalized_pose_backend(context.processing_settings)
    frames = frame_inventory(frames_root(context)).frames
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


def build_camera_motion_command(context: ProcessingTaskContext) -> ProcessingCommand | list[ProcessingCommand]:
    backend = normalized_pose_backend(context.processing_settings)
    frames = frame_inventory(frames_root(context)).frames

    if backend == "stub":
        return placeholder_command(
            "camera_motion_command.json",
            f"pose_backend=stub source={context.upload_path.name}",
        )

    if backend == "colmap":
        colmap_command = resolve_command(context.processing_settings.pose_command, "colmap")
        if not colmap_command:
            raise ProcessingTaskFailed("Pose backend colmap selected but COLMAP binary was not found.")

        return [
            ProcessingCommand(
                artifact_name=command.artifact_name,
                command=command.command,
                timeout_sec=_colmap_command_timeout_sec(
                    context.processing_settings,
                    command.artifact_name,
                    len(frames),
                ),
            )
            for command in build_colmap_pipeline_commands(
                colmap_command,
                context.artifacts_root,
                frames_root(context),
            )
        ]

    if backend == "droid_slam":
        raise ProcessingTaskFailed("Pose backend droid_slam is configured but not implemented yet.")

    raise ProcessingTaskFailed(f"Unsupported pose backend: {context.processing_settings.pose_backend}")


def normalized_pose_backend(settings: ProcessingSettings) -> str:
    return settings.pose_backend.strip().lower()


def _colmap_command_timeout_sec(
    settings: ProcessingSettings,
    artifact_name: str,
    frame_count: int,
) -> float:
    if artifact_name != "colmap_mapper_command.json":
        return settings.pose_timeout_sec

    # Favor the mapper budget on longer clips because local COLMAP runtimes vary materially with frame count.
    adaptive_timeout_sec = max(
        settings.pose_timeout_sec,
        COLMAP_MAPPER_MIN_TIMEOUT_SEC,
        frame_count * COLMAP_MAPPER_TIMEOUT_PER_FRAME_SEC,
    )
    return float(min(adaptive_timeout_sec, COLMAP_MAPPER_MAX_TIMEOUT_SEC))


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
