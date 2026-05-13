from fastapi.testclient import TestClient

from remote_dense_app.main import RemoteDenseSettings, create_app
from test_helpers import build_bundle_bytes


def test_submit_job_returns_remote_job_id_and_posts_callback(tmp_path) -> None:
    app = create_app(RemoteDenseSettings(repo_root=tmp_path, backend="mock"))
    client = TestClient(app)
    captured = {}

    def fake_callback_sender(callback_url, callback_token, dense_ply, remote_job_id, timeout_sec):
        captured["callback_url"] = callback_url
        captured["callback_token"] = callback_token
        captured["dense_ply"] = dense_ply
        captured["remote_job_id"] = remote_job_id
        captured["timeout_sec"] = timeout_sec

    app.state.callback_sender = fake_callback_sender

    response = client.post(
        "/jobs",
        data={
            "job_id": "scene_abc123",
            "callback_url": "https://dreamnav.example/jobs/scene_abc123/remote-dense-result",
            "callback_token": "callback-secret",
            "source_video": "walkthrough.mov",
        },
        files={"bundle": ("remote_dense_bundle.zip", build_bundle_bytes(), "application/zip")},
    )

    assert response.status_code == 200
    assert response.json()["remote_job_id"].startswith("remote_")
    assert response.json()["backend"] == "mock"
    assert response.json()["warnings"] == []
    assert captured["callback_token"] == "callback-secret"
    assert captured["callback_url"].endswith("/remote-dense-result")
    assert captured["dense_ply"].startswith(b"ply\nformat ascii 1.0\n")
