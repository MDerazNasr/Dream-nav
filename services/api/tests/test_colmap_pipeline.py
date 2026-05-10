from pathlib import Path

from app.colmap_pipeline import build_colmap_pipeline_commands


def test_build_colmap_pipeline_commands_are_ordered(tmp_path: Path) -> None:
    commands = build_colmap_pipeline_commands(
        "/opt/bin/colmap",
        tmp_path / "artifacts",
        tmp_path / "artifacts" / "frames",
    )

    assert [command.command[1] for command in commands] == [
        "feature_extractor",
        "exhaustive_matcher",
        "mapper",
        "model_converter",
    ]
    assert [command.artifact_name for command in commands] == [
        "colmap_feature_extractor_command.json",
        "colmap_exhaustive_matcher_command.json",
        "colmap_mapper_command.json",
        "colmap_model_converter_command.json",
    ]
    assert "--output_type" in commands[-1].command
    assert (tmp_path / "artifacts" / "colmap" / "sparse").is_dir()
