from fastapi.testclient import TestClient

from remote_dense_app.main import RemoteDenseSettings, create_app


def test_submit_job_returns_remote_job_id_and_posts_callback(tmp_path) -> None:
    app = create_app(RemoteDenseSettings(repo_root=tmp_path))
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
    assert captured["callback_token"] == "callback-secret"
    assert captured["callback_url"].endswith("/remote-dense-result")
    assert captured["dense_ply"].startswith(b"ply\nformat ascii 1.0\n")


def build_bundle_bytes() -> bytes:
    from io import BytesIO
    from json import dumps
    from zipfile import ZipFile

    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "manifest.json",
            dumps(
                {
                    "job_id": "scene_abc123",
                    "source_video": "walkthrough.mov",
                    "frame_count": 3,
                    "callback_url": "https://dreamnav.example/jobs/scene_abc123/remote-dense-result",
                    "callback_token": "callback-secret",
                }
            ),
        )
        archive.writestr(
            "artifacts/camera_path.json",
            dumps(
                {
                    "scene_id": "scene_abc123",
                    "poses": [
                        {"position": [0, 1.55, 0]},
                        {"position": [0.2, 1.55, -0.8]},
                    ]
                }
            ),
        )
        archive.writestr("artifacts/camera_motion.json", "{}")
        archive.writestr("artifacts/frame_extraction.json", "{}")
        archive.writestr("artifacts/metadata.json", "{}")
        archive.writestr("frames/frame_0000.jpg", b"\xff\xd8\xff")
        archive.writestr("frames/frame_0001.jpg", b"\xff\xd8\xff")
        archive.writestr("frames/frame_0002.jpg", b"\xff\xd8\xff")
    return buffer.getvalue()
