from pathlib import Path

import pytest

from app.colmap_model_selection import ColmapModelSelectionError, select_and_export_colmap_model


def test_select_and_export_colmap_model_chooses_largest_model(tmp_path: Path) -> None:
    fake_colmap = _fake_colmap(tmp_path)
    sparse_root = tmp_path / "colmap" / "sparse"
    (sparse_root / "0").mkdir(parents=True)
    (sparse_root / "1").mkdir()
    output_root = tmp_path / "colmap"

    selection = select_and_export_colmap_model(str(fake_colmap), sparse_root, output_root)

    assert selection.selected_model == "1"
    assert selection.registered_image_count == 3
    assert (output_root / "cameras.txt").is_file()
    assert (output_root / "images.txt").read_text(encoding="utf-8").count("frame_") == 3
    assert (output_root / "colmap_model_selection.json").is_file()


def test_select_and_export_colmap_model_rejects_missing_sparse_root(tmp_path: Path) -> None:
    with pytest.raises(ColmapModelSelectionError, match="did not create a sparse model directory"):
        select_and_export_colmap_model("/missing/colmap", tmp_path / "missing", tmp_path)


def test_select_and_export_colmap_model_rejects_empty_models(tmp_path: Path) -> None:
    fake_colmap = _fake_colmap(tmp_path, write_empty=True)
    sparse_root = tmp_path / "colmap" / "sparse"
    (sparse_root / "0").mkdir(parents=True)

    with pytest.raises(ColmapModelSelectionError, match="did not contain registered images"):
        select_and_export_colmap_model(str(fake_colmap), sparse_root, tmp_path / "colmap")


def _fake_colmap(tmp_path: Path, write_empty: bool = False) -> Path:
    fake_colmap = tmp_path / "fake_colmap.py"
    image_rows_by_model = {
        "0": "1 1 0 0 0 0 0 0 1 frame_0000.jpg\n\n",
        "1": (
            "1 1 0 0 0 0 0 0 1 frame_0000.jpg\n\n"
            "2 1 0 0 0 -1 -2 -3 1 frame_0001.jpg\n\n"
            "3 1 0 0 0 -2 -4 -6 1 frame_0002.jpg\n\n"
        ),
    }
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        "input_path = Path(sys.argv[sys.argv.index('--input_path') + 1])\n"
        "output_path = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "output_path.mkdir(parents=True, exist_ok=True)\n"
        "(output_path / 'cameras.txt').write_text('1 PINHOLE 1920 1080 1200 1210 960 540\\n')\n"
        + (
            "(output_path / 'images.txt').write_text('')\n"
            if write_empty
            else f"(output_path / 'images.txt').write_text({image_rows_by_model!r}.get(input_path.name, ''))\n"
        )
        + "(output_path / 'points3D.txt').write_text('')\n",
        encoding="utf-8",
    )
    fake_colmap.chmod(0o755)
    return fake_colmap
