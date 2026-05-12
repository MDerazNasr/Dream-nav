from pathlib import Path

import pytest

from app.colmap_sparse_to_splat import ColmapSparseToSplatError, build_splat_from_colmap_points


def test_build_splat_from_colmap_points_writes_binary_ply(tmp_path: Path) -> None:
    (tmp_path / "points3D.txt").write_text(
        "# point data\n"
        "1 0.0 1.0 -2.0 255 0 0 0.5 1 1 2\n"
        "2 0.5 1.2 -2.4 0 255 128 1.0 1 2 2\n",
        encoding="utf-8",
    )

    vertex_count = build_splat_from_colmap_points(tmp_path, tmp_path / "splat.ply")
    payload = (tmp_path / "splat.ply").read_bytes()

    assert vertex_count == 2
    assert payload.startswith(b"ply\nformat binary_little_endian 1.0")
    assert b"element vertex 2" in payload.split(b"end_header\n", 1)[0]


def test_build_splat_from_colmap_points_rejects_missing_points(tmp_path: Path) -> None:
    with pytest.raises(ColmapSparseToSplatError, match="points3D.txt is missing"):
        build_splat_from_colmap_points(tmp_path, tmp_path / "splat.ply")


def test_build_splat_from_colmap_points_rejects_empty_points(tmp_path: Path) -> None:
    (tmp_path / "points3D.txt").write_text("# no usable points\n", encoding="utf-8")

    with pytest.raises(ColmapSparseToSplatError, match="did not contain usable sparse points"):
        build_splat_from_colmap_points(tmp_path, tmp_path / "splat.ply")
