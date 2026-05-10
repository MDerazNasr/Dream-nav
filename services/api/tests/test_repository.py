from pathlib import Path

import pytest

from app.repository import SceneDataError, SceneNotFoundError, SceneRepository


def test_repository_rejects_malformed_registry(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "demo-scenes.json").write_text("{}", encoding="utf-8")
    repo = SceneRepository(data_root)

    with pytest.raises(SceneDataError, match="registry must be a list"):
        repo.list_demo_scenes()


def test_repository_rejects_unknown_scene() -> None:
    repo = SceneRepository(Path("data"))

    with pytest.raises(SceneNotFoundError):
        repo.get_quality_report("missing_scene")


def test_repository_reports_available_splat_asset() -> None:
    repo = SceneRepository(Path("data"))

    status = repo.get_asset_status("warehouse_01")

    assert status.splat_available is True
    assert status.viewer_render_mode == "splat"
