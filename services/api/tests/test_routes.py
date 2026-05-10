from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "dreamnav-api"}


def test_demo_scenes_returns_locked_scene() -> None:
    client = TestClient(create_app())

    response = client.get("/demo-scenes")

    assert response.status_code == 200
    assert response.json()[0]["scene_id"] == "warehouse_01"


def test_scene_assets_match_spec_urls() -> None:
    client = TestClient(create_app())

    response = client.get("/scene/warehouse_01")

    assert response.status_code == 200
    assert response.json()["splat_url"] == "/scenes/warehouse_01/splat.ply"


def test_quality_returns_scene_metrics() -> None:
    client = TestClient(create_app())

    response = client.get("/quality/warehouse_01")

    assert response.status_code == 200
    assert response.json()["runtime_path"] == "torch_fp16"


def test_missing_scene_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/scene/missing_scene")

    assert response.status_code == 404
    assert response.json()["detail"] == "Scene not found"


def test_missing_quality_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/quality/missing_scene")

    assert response.status_code == 404
    assert response.json()["detail"] == "Scene not found"


def test_static_scene_metadata_is_served() -> None:
    client = TestClient(create_app())

    response = client.get("/scenes/warehouse_01/metadata.json")

    assert response.status_code == 200
    assert response.json()["scene_id"] == "warehouse_01"
