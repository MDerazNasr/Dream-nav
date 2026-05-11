from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .processing_command_utils import placeholder_command, resolve_command
from .processing_models import ProcessingCommand, ProcessingTaskContext, ProcessingTaskFailed, ProcessingTaskResult
from .config import ProcessingSettings
from .video_probe import VideoProbeError, probe_video_file


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


def extract_video_frames(context: ProcessingTaskContext) -> ProcessingTaskResult:
    backend = normalized_frame_backend(context.processing_settings)
    _validate_frame_settings(context)
    root = frames_root(context)
    root.mkdir(parents=True, exist_ok=True)

    if backend == "stub" and not frame_inventory(root).frames:
        for frame_index in range(3):
            (root / f"frame_{frame_index:04d}.jpg").write_text(
                f"stub frame {frame_index}\n",
                encoding="utf-8",
            )

    inventory = frame_inventory(root)
    _validate_frame_inventory(inventory, context, backend)
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
        frames_path=str(root),
        warnings=warnings,
    )


def build_frame_extraction_command(context: ProcessingTaskContext) -> ProcessingCommand:
    backend = normalized_frame_backend(context.processing_settings)
    _validate_frame_settings(context)
    root = frames_root(context)
    root.mkdir(parents=True, exist_ok=True)

    if backend == "stub":
        return placeholder_command(
            "frame_extraction_command.json",
            f"frame_backend=stub source={context.upload_path.name} frames={root}",
        )

    if backend == "ffmpeg":
        ffmpeg_command = resolve_command(context.processing_settings.frame_command, "ffmpeg")
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
                str(root / "frame_%04d.jpg"),
            ],
            timeout_sec=context.processing_settings.frame_timeout_sec,
        )

    raise ProcessingTaskFailed(f"Unsupported frame backend: {context.processing_settings.frame_backend}")


def normalized_frame_backend(settings: ProcessingSettings) -> str:
    return settings.frame_backend.strip().lower()


def frames_root(context: ProcessingTaskContext) -> Path:
    return context.artifacts_root / "frames"


def frame_inventory(root: Path) -> FrameInventory:
    return FrameInventory(sorted(frame for frame in root.glob("*.jpg") if frame.is_file()))


def _validate_frame_settings(context: ProcessingTaskContext) -> None:
    settings = context.processing_settings
    if settings.frame_rate <= 0:
        raise ProcessingTaskFailed("Frame rate must be greater than zero.")

    if settings.frame_max_count < 1:
        raise ProcessingTaskFailed("Frame max count must be at least one.")

    if settings.frame_max_duration_sec <= 0:
        raise ProcessingTaskFailed("Frame max duration must be greater than zero.")


def _validate_frame_inventory(
    inventory: FrameInventory,
    context: ProcessingTaskContext,
    backend: str,
) -> None:
    if inventory.frame_count == 0:
        raise ProcessingTaskFailed("Frame extraction produced no JPG frames.")

    if inventory.frame_count > context.processing_settings.frame_max_count:
        raise ProcessingTaskFailed(
            f"Frame extraction produced {inventory.frame_count} frames, above configured limit {context.processing_settings.frame_max_count}."
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
