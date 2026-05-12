from app.main import create_app
from app.repository import SceneRepository
from fastapi.testclient import TestClient


def test_demo_readiness_reports_locked_scene_status() -> None:
    client = TestClient(create_app())

    response = client.get("/demo-readiness/warehouse_01")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scene_id"] == "warehouse_01"
    assert payload["locked_scene"] is True
    assert payload["required_assets_present"] is True
    assert payload["fallback_assets_present"] is True
    assert payload["viewer_render_mode"] == "splat"
    assert payload["status"] == "degraded"
    assert payload["warnings"] == ["Completion must stay labeled as lower confidence."]


def test_demo_readiness_returns_404_for_missing_scene() -> None:
    client = TestClient(create_app())

    response = client.get("/demo-readiness/missing_scene")

    assert response.status_code == 404
    assert response.json()["detail"] == "Scene not found"


def test_repository_derives_demo_readiness_from_scene_assets() -> None:
    repo = SceneRepository(create_app().state.settings.data_root)

    readiness = repo.get_demo_readiness("warehouse_01")

    assert readiness.required_assets_present is True
    assert readiness.fallback_assets_present is True
    assert readiness.cached_completion is True
