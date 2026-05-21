from __future__ import annotations

from .gaussian_import_validation import evaluate_imported_scene
from .jobs import JobArtifactNotFoundError, JobRepository
from .schemas import GaussianImportResponse
from .splat_assets import SplatAssetError, import_job_splat_asset
from .viewer_assets import ViewerAssetBuildError, build_job_viewer_assets


class GaussianImportError(Exception):
    pass


def apply_imported_gaussian_asset(
    job_repository: JobRepository,
    job_id: str,
    file_name: str,
    payload: bytes,
    source_coordinate_system: str | None = None,
    source_coordinate_metadata: dict[str, object] | None = None,
) -> GaussianImportResponse:
    previous_gaussian_scene = _optional_job_artifact(job_repository, job_id, "gaussian_scene.json")
    previous_visibility = _optional_job_artifact(job_repository, job_id, "visibility_manifest.json")
    previous_quality = _optional_job_artifact(job_repository, job_id, "quality.json")

    try:
        imported = import_job_splat_asset(
            job_repository.artifact_root(job_id),
            file_name,
            payload,
            source_coordinate_system=source_coordinate_system,
            source_coordinate_metadata=source_coordinate_metadata,
        )
    except SplatAssetError as error:
        raise GaussianImportError(str(error)) from error

    source_video = job_source_video(job_id, job_repository)
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
        raise GaussianImportError(str(error)) from error

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

    response = GaussianImportResponse(
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
    job_repository.write_artifact(job_id, "gaussian_import_review.json", response.model_dump())
    return response


def job_source_video(job_id: str, job_repository: JobRepository) -> str:
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
