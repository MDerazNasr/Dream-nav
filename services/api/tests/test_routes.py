from pathlib import Path

from fastapi.testclient import TestClient

from app.config import ApiSettings
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


def test_asset_status_reports_splat_mode_when_splat_exists() -> None:
    client = TestClient(create_app())

    response = client.get("/scene/warehouse_01/asset-status")

    assert response.status_code == 200
    assert response.json()["viewer_render_mode"] == "splat"
    assert response.json()["missing_assets"] == []


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


def test_upload_creates_processing_job(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))

    response = client.post(
        "/upload",
        files={"file": ("walkthrough.mp4", b"video-bytes", "video/mp4")},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["job_id"].startswith("scene_")
    assert payload["validation_status"] == "pass"
    assert payload["warnings"] == []
    assert (tmp_path / "data" / "uploads" / payload["job_id"] / "walkthrough.mp4").is_file()


def test_upload_warns_for_unsupported_video_extension(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))

    response = client.post(
        "/upload",
        files={"file": ("walkthrough.txt", b"not-video", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["validation_status"] == "warning"
    assert response.json()["warnings"] == [
        "Use MP4, MOV, or M4V walkthrough videos for reconstruction."
    ]


def test_status_returns_processing_progress(tmp_path: Path) -> None:
    client = TestClient(create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False)))
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]

    response = client.get(f"/status/{job_id}")

    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    assert response.json()["state"] == "queued"
    assert response.json()["stage"] == "checking_capture_quality"
    assert response.json()["progress"] == 0
    assert response.json()["output_scene_id"] is None
    assert response.json()["failed_stage"] is None
    assert response.json()["failed_artifact"] is None


def test_status_returns_failed_job_state(tmp_path: Path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    upload_response = client.post(
        "/upload",
        files={"file": ("walkthrough.mov", b"video-bytes", "video/quicktime")},
    )
    job_id = upload_response.json()["job_id"]
    app.state.job_repository.fail_job(
        job_id,
        "Bad poses break splat",
        failed_stage="estimating_camera_motion",
        failed_artifact="camera_motion_command.json",
    )

    response = client.get(f"/status/{job_id}")

    assert response.status_code == 200
    assert response.json()["state"] == "failed"
    assert response.json()["stage"] == "failed"
    assert response.json()["error_message"] == "Bad poses break splat"
    assert response.json()["failed_stage"] == "estimating_camera_motion"
    assert response.json()["failed_artifact"] == "camera_motion_command.json"


def test_missing_job_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/status/scene_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"
