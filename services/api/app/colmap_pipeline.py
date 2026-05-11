from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class ColmapPipelineCommand:
    artifact_name: str
    command: list[str]


def build_colmap_pipeline_commands(
    colmap_command: str,
    artifacts_root: Path,
    frames_root: Path,
) -> list[ColmapPipelineCommand]:
    colmap_root = artifacts_root / "colmap"
    sparse_root = colmap_root / "sparse"
    database_path = colmap_root / "database.db"
    colmap_root.mkdir(parents=True, exist_ok=True)
    sparse_root.mkdir(parents=True, exist_ok=True)

    return [
        ColmapPipelineCommand(
            artifact_name="colmap_feature_extractor_command.json",
            command=[
                colmap_command,
                "feature_extractor",
                "--database_path",
                str(database_path),
                "--image_path",
                str(frames_root),
            ],
        ),
        ColmapPipelineCommand(
            artifact_name="colmap_exhaustive_matcher_command.json",
            command=[
                colmap_command,
                "exhaustive_matcher",
                "--database_path",
                str(database_path),
            ],
        ),
        ColmapPipelineCommand(
            artifact_name="colmap_mapper_command.json",
            command=[
                colmap_command,
                "mapper",
                "--database_path",
                str(database_path),
                "--image_path",
                str(frames_root),
                "--output_path",
                str(sparse_root),
            ],
        ),
        ColmapPipelineCommand(
            artifact_name="colmap_model_selection_command.json",
            command=[
                sys.executable,
                str(Path(__file__).with_name("colmap_model_selection.py")),
                "--colmap-command",
                colmap_command,
                "--sparse-root",
                str(sparse_root),
                "--output-root",
                str(colmap_root),
            ],
        ),
    ]
