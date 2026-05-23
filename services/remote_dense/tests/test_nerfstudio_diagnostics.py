from pathlib import Path

import pytest

from remote_dense_app import nerfstudio_diagnostics


def test_collect_render_pairs_matches_rgb_and_gt_outputs(tmp_path: Path) -> None:
    image = pytest.importorskip("PIL.Image", reason="Pillow not installed in local test venv")
    root = tmp_path / "dataset-renders" / "train"
    rgb = root / "rgb"
    gt = root / "gt-rgb"
    (rgb / "nested").mkdir(parents=True)
    (gt / "nested").mkdir(parents=True)
    image.new("RGB", (8, 8), color=(255, 0, 0)).save(rgb / "nested" / "frame_0001.jpg")
    image.new("RGB", (8, 8), color=(0, 255, 0)).save(gt / "nested" / "frame_0001.jpg")
    image.new("RGB", (8, 8), color=(0, 0, 255)).save(rgb / "nested" / "frame_0002.png")

    pairs = nerfstudio_diagnostics.collect_render_pairs(tmp_path / "dataset-renders")

    assert len(pairs) == 1
    assert pairs[0][2] == "nested/frame_0001"


def test_evenly_sample_pairs_spans_dataset() -> None:
    pairs = [(Path(f"gt-{index}.png"), Path(f"rgb-{index}.png"), f"frame_{index:04d}") for index in range(10)]

    sampled = nerfstudio_diagnostics.evenly_sample_pairs(pairs, 4)

    assert [label for _, _, label in sampled] == ["frame_0000", "frame_0003", "frame_0006", "frame_0009"]


def test_write_contact_sheet_creates_summary_image(tmp_path: Path) -> None:
    image = pytest.importorskip("PIL.Image", reason="Pillow not installed in local test venv")
    pairs = []
    for index in range(2):
        gt_path = tmp_path / f"gt_{index}.png"
        rgb_path = tmp_path / f"rgb_{index}.png"
        image.new("RGB", (12, 8), color=(255, 255 - index * 10, 255)).save(gt_path)
        image.new("RGB", (12, 8), color=(index * 10, 0, 0)).save(rgb_path)
        pairs.append((gt_path, rgb_path, f"frame_{index:04d}"))

    summary_path = nerfstudio_diagnostics.write_contact_sheet(tmp_path, pairs, sample_count=2)

    assert summary_path.is_file()
    opened = image.open(summary_path)
    try:
        assert opened.width > 24
        assert opened.height > 16
    finally:
        opened.close()


def test_summarize_render_pairs_reports_best_and_worst_frames(tmp_path: Path) -> None:
    image = pytest.importorskip("PIL.Image", reason="Pillow not installed in local test venv")
    pairs = []
    for index, delta in enumerate((0, 16, 64), start=1):
        gt_path = tmp_path / f"gt_{index}.png"
        rgb_path = tmp_path / f"rgb_{index}.png"
        image.new("RGB", (4, 4), color=(128, 128, 128)).save(gt_path)
        image.new("RGB", (4, 4), color=(128 + delta, 128, 128)).save(rgb_path)
        pairs.append((gt_path, rgb_path, f"frame_{index:04d}"))

    summary = nerfstudio_diagnostics.summarize_render_pairs(pairs)

    assert summary["best_frames"][0]["label"] == "frame_0001"
    assert summary["worst_frames"][0]["label"] == "frame_0003"
    assert summary["mean_mae"] > 0
    assert summary["median_mae"] > 0
