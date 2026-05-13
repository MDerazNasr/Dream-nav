from fastapi.testclient import TestClient

from app.config import ApiSettings
from app.main import create_app
from app.remote_dense_handoff import RemoteDenseSubmissionResult
from tests.test_gaussian_import_routes import _completed_job, _point_cloud_ply


def test_submit_remote_dense_route_packages_completed_job(tmp_path, monkeypatch) -> None:
    app = create_app(
        ApiSettings(
            repo_root=tmp_path,
            auto_start_worker=False,
            public_api_base_url="https://dreamnav.example",
            remote_dense_url="https://dense.example/jobs",
            remote_dense_token="provider-secret",
            remote_dense_callback_token="callback-secret",
        )
    )
    client = TestClient(app)
    job_id = _completed_job(client, app)
    _write_remote_frames(app.state.job_repository, job_id)

    def fake_submit(provider_url, bundle, callback_token, provider_token=None, sender=None):
        assert provider_url == "https://dense.example/jobs"
        assert callback_token == "callback-secret"
        assert provider_token == "provider-secret"
        assert bundle.path.is_file()
        return RemoteDenseSubmissionResult(
            bundle=bundle,
            provider_url=provider_url,
            remote_job_id="remote_001",
            submission_status="submitted",
            backend="colmap_dense",
            warnings=[],
        )

    monkeypatch.setattr("app.routes.submit_remote_dense_job", fake_submit)

    response = client.post(f"/jobs/{job_id}/submit-remote-dense")

    assert response.status_code == 200
    assert response.json()["remote_job_id"] == "remote_001"
    assert response.json()["backend"] == "colmap_dense"
    assert response.json()["frame_count"] == 3
    assert response.json()["callback_url"] == f"https://dreamnav.example/jobs/{job_id}/remote-dense-result"
    submission_artifact = app.state.job_repository.read_artifact(job_id, "remote_dense_submission.json")
    assert submission_artifact["backend"] == "colmap_dense"
    assert submission_artifact["bundle_file"] == "remote_dense_bundle.zip"


def test_submit_remote_dense_route_requires_configuration(tmp_path) -> None:
    app = create_app(ApiSettings(repo_root=tmp_path, auto_start_worker=False))
    client = TestClient(app)
    job_id = _completed_job(client, app)

    response = client.post(f"/jobs/{job_id}/submit-remote-dense")

    assert response.status_code == 409
    assert response.json()["detail"] == "Remote dense backend is not configured"


def test_remote_dense_result_route_requires_callback_token(tmp_path) -> None:
    app = create_app(
        ApiSettings(
            repo_root=tmp_path,
            auto_start_worker=False,
            remote_dense_callback_token="callback-secret",
        )
    )
    client = TestClient(app)
    job_id = _completed_job(client, app)

    response = client.post(
        f"/jobs/{job_id}/remote-dense-result",
        files={"file": ("dense_scene.ply", _point_cloud_ply(12001), "application/octet-stream")},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Remote dense callback token is invalid"


def test_remote_dense_result_route_imports_dense_asset(tmp_path) -> None:
    app = create_app(
        ApiSettings(
            repo_root=tmp_path,
            auto_start_worker=False,
            remote_dense_callback_token="callback-secret",
        )
    )
    client = TestClient(app)
    job_id = _completed_job(client, app)

    response = client.post(
        f"/jobs/{job_id}/remote-dense-result",
        headers={
            "X-DreamNav-Callback-Token": "callback-secret",
            "X-DreamNav-Remote-Backend": "mock",
            "X-DreamNav-Remote-Job-Id": "remote_001",
        },
        files={"file": ("dense_scene.ply", _point_cloud_ply(12001), "application/octet-stream")},
    )

    assert response.status_code == 200
    assert response.json()["validation_status"] == "pass"
    review_artifact = app.state.job_repository.read_artifact(job_id, "gaussian_import_review.json")
    result_artifact = app.state.job_repository.read_artifact(job_id, "remote_dense_result.json")
    assert review_artifact["gaussian_count"] == 12001
    assert result_artifact["backend"] == "mock"
    assert result_artifact["remote_job_id"] == "remote_001"
    assert result_artifact["validation_status"] == "pass"


def _write_remote_frames(job_repository, job_id: str) -> None:
    frames_root = job_repository.artifact_root(job_id) / "frames"
    frames_root.mkdir(parents=True, exist_ok=True)
    for frame_index in range(3):
        (frames_root / f"frame_{frame_index:04d}.jpg").write_bytes(b"\xff\xd8\xff")
