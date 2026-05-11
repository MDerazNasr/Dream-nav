from __future__ import annotations

from dataclasses import asdict, dataclass
from json import dumps
from pathlib import Path
from shutil import copyfile
from subprocess import run
from sys import argv, exit


class ColmapModelSelectionError(Exception):
    pass


@dataclass(frozen=True)
class ColmapModelCandidate:
    model_name: str
    input_path: str
    text_path: str
    registered_image_count: int


@dataclass(frozen=True)
class ColmapModelSelection:
    selected_model: str
    selected_text_path: str
    registered_image_count: int
    candidates: list[ColmapModelCandidate]

    def to_artifact(self) -> dict[str, object]:
        return {
            "selected_model": self.selected_model,
            "selected_text_path": self.selected_text_path,
            "registered_image_count": self.registered_image_count,
            "candidates": [asdict(candidate) for candidate in self.candidates],
        }


def select_and_export_colmap_model(
    colmap_command: str,
    sparse_root: Path,
    output_root: Path,
) -> ColmapModelSelection:
    model_roots = _model_roots(sparse_root)
    text_root = output_root / "model_candidates"
    text_root.mkdir(parents=True, exist_ok=True)

    candidates = [
        _convert_and_describe_model(colmap_command, model_root, text_root / model_root.name)
        for model_root in model_roots
    ]
    selected = max(candidates, key=lambda candidate: candidate.registered_image_count)
    if selected.registered_image_count == 0:
        raise ColmapModelSelectionError("COLMAP sparse models did not contain registered images.")

    selected_root = Path(selected.text_path)
    _copy_selected_text_model(selected_root, output_root)
    artifact = ColmapModelSelection(
        selected_model=selected.model_name,
        selected_text_path=selected.text_path,
        registered_image_count=selected.registered_image_count,
        candidates=candidates,
    )
    (output_root / "colmap_model_selection.json").write_text(
        dumps(artifact.to_artifact(), indent=2),
        encoding="utf-8",
    )
    return artifact


def _model_roots(sparse_root: Path) -> list[Path]:
    if not sparse_root.is_dir():
        raise ColmapModelSelectionError("COLMAP mapper did not create a sparse model directory.")

    model_roots = sorted(path for path in sparse_root.iterdir() if path.is_dir())
    if not model_roots:
        raise ColmapModelSelectionError("COLMAP mapper produced no sparse models.")

    return model_roots


def _convert_and_describe_model(
    colmap_command: str,
    model_root: Path,
    text_output_root: Path,
) -> ColmapModelCandidate:
    text_output_root.mkdir(parents=True, exist_ok=True)
    completed = run(
        [
            colmap_command,
            "model_converter",
            "--input_path",
            str(model_root),
            "--output_path",
            str(text_output_root),
            "--output_type",
            "TXT",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise ColmapModelSelectionError(
            f"COLMAP model_converter failed for sparse model {model_root.name}."
        )

    return ColmapModelCandidate(
        model_name=model_root.name,
        input_path=str(model_root),
        text_path=str(text_output_root),
        registered_image_count=_registered_image_count(text_output_root / "images.txt"),
    )


def _registered_image_count(images_path: Path) -> int:
    if not images_path.is_file():
        return 0

    return sum(
        1
        for line in images_path.read_text(encoding="utf-8").splitlines()
        if _is_image_pose_line(line)
    )


def _is_image_pose_line(line: str) -> bool:
    if not line.strip() or line.lstrip().startswith("#"):
        return False

    return len(line.split()) >= 10


def _copy_selected_text_model(selected_root: Path, output_root: Path) -> None:
    for artifact_name in ("cameras.txt", "images.txt", "points3D.txt"):
        source = selected_root / artifact_name
        if source.is_file():
            copyfile(source, output_root / artifact_name)

    if not (output_root / "cameras.txt").is_file() or not (output_root / "images.txt").is_file():
        raise ColmapModelSelectionError("Selected COLMAP model did not export cameras.txt and images.txt.")


def main(args: list[str]) -> int:
    parsed_args = _parse_args(args)
    try:
        selection = select_and_export_colmap_model(
            parsed_args["colmap_command"],
            Path(parsed_args["sparse_root"]),
            Path(parsed_args["output_root"]),
        )
    except ColmapModelSelectionError as error:
        print(str(error))
        return 1

    print(f"selected_colmap_model={selection.selected_model} images={selection.registered_image_count}")
    return 0


def _parse_args(args: list[str]) -> dict[str, str]:
    if len(args) != 6 or args[0] != "--colmap-command" or args[2] != "--sparse-root" or args[4] != "--output-root":
        raise SystemExit("Usage: colmap_model_selection.py --colmap-command <cmd> --sparse-root <path> --output-root <path>")

    return {
        "colmap_command": args[1],
        "sparse_root": args[3],
        "output_root": args[5],
    }


if __name__ == "__main__":
    exit(main(argv[1:]))
