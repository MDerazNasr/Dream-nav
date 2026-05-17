from json import loads
from os import utime
from threading import Event, Thread

from fastapi.testclient import TestClient
from unittest.mock import patch

from remote_dense_app.main import RemoteDenseSettings, _process_submission, create_app, default_settings
from remote_dense_app.backend import DenseBuildResult
from test_helpers import build_bundle_bytes


def test_submit_job_returns_remote_job_id_and_posts_callback(tmp_path) -> None:
    app = create_app(RemoteDenseSettings(repo_root=tmp_path, backend="mock"))
    client = TestClient(app)
    captured = {}

    def fake_callback_sender(callback_url, callback_token, dense_ply, remote_job_id, backend, timeout_sec):
        captured["callback_url"] = callback_url
        captured["callback_token"] = callback_token
        captured["dense_ply"] = dense_ply
        captured["remote_job_id"] = remote_job_id
        captured["backend"] = backend
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
    assert response.json()["bundle_file"] == "bundle.zip"
    assert captured["callback_token"] == "callback-secret"
    assert captured["callback_url"].endswith("/remote-dense-result")
    assert captured["backend"] == "mock"
    assert captured["dense_ply"].startswith(b"ply\nformat ascii 1.0\n")
    assert captured["remote_job_id"] == response.json()["remote_job_id"]

    job_root = tmp_path / ".context" / "remote-dense-submissions" / response.json()["remote_job_id"]
    assert (job_root / "bundle.zip").is_file()
    result = loads((job_root / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "completed"
    assert result["backend"] == "mock"
    assert result["error"] is None


def test_submit_job_records_failed_status_when_callback_fails(tmp_path) -> None:
    app = create_app(RemoteDenseSettings(repo_root=tmp_path, backend="mock"))
    client = TestClient(app)

    def fake_callback_sender(*_args):
        raise RuntimeError("callback failed")

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
    job_root = tmp_path / ".context" / "remote-dense-submissions" / response.json()["remote_job_id"]
    result = loads((job_root / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert result["backend"] == "mock"
    assert result["error"] == "callback failed"


def test_job_status_route_returns_recorded_remote_result(tmp_path) -> None:
    app = create_app(RemoteDenseSettings(repo_root=tmp_path, backend="mock"))
    client = TestClient(app)
    app.state.callback_sender = lambda *args: None

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

    remote_job_id = response.json()["remote_job_id"]
    status_response = client.get(f"/jobs/{remote_job_id}")

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["backend"] == "mock"


def test_submit_job_prunes_old_remote_workspaces(tmp_path) -> None:
    app = create_app(RemoteDenseSettings(repo_root=tmp_path, backend="mock", retained_job_count=2))
    client = TestClient(app)
    app.state.callback_sender = lambda *args: None
    root = tmp_path / ".context" / "remote-dense-submissions"
    stale_jobs = [root / "remote_old_a", root / "remote_old_b"]
    for index, stale_job in enumerate(stale_jobs, start=1):
        stale_job.mkdir(parents=True, exist_ok=True)
        (stale_job / "bundle.zip").write_bytes(b"zip")
        utime(stale_job, (index, index))

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
    assert not stale_jobs[0].exists()
    assert stale_jobs[1].exists()


def test_default_settings_prefers_bundled_command_adapter(monkeypatch) -> None:
    for name in (
        "DREAMNAV_REMOTE_GAUSSIAN_COMMAND",
        "DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE",
        "DREAMNAV_REMOTE_DENSE_COMMAND",
        "DREAMNAV_REMOTE_DENSE_BACKEND",
        "DREAMNAV_REMOTE_DENSE_COLMAP_COMMAND",
        "DREAMNAV_REMOTE_DENSE_ALLOW_MOCK_FALLBACK",
        "DREAMNAV_REMOTE_DENSE_RETAINED_JOBS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = default_settings()

    assert settings.gaussian_command is None
    assert settings.dense_command is not None
    assert settings.dense_command.endswith("remote_dense_app/colmap_command_adapter.py")


def test_default_settings_prefers_bundled_docker_adapter_when_image_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("DREAMNAV_REMOTE_DENSE_DOCKER_IMAGE", "dreamnav/dense-engine:latest")
    for name in (
        "DREAMNAV_REMOTE_GAUSSIAN_COMMAND",
        "DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE",
        "DREAMNAV_REMOTE_DENSE_COMMAND",
        "DREAMNAV_REMOTE_DENSE_BACKEND",
        "DREAMNAV_REMOTE_DENSE_COLMAP_COMMAND",
        "DREAMNAV_REMOTE_DENSE_ALLOW_MOCK_FALLBACK",
        "DREAMNAV_REMOTE_DENSE_RETAINED_JOBS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = default_settings()

    assert settings.gaussian_command is None
    assert settings.dense_command is not None
    assert settings.dense_command.endswith("remote_dense_app/docker_command_adapter.py")


def test_default_settings_reads_trained_gaussian_command(monkeypatch) -> None:
    monkeypatch.setenv("DREAMNAV_REMOTE_GAUSSIAN_COMMAND", "/opt/dreamnav/gaussian-backend")

    settings = default_settings()

    assert settings.gaussian_command == "/opt/dreamnav/gaussian-backend"


def test_default_settings_prefers_bundled_gaussian_adapter_when_engine_is_configured(monkeypatch) -> None:
    for name in (
        "DREAMNAV_REMOTE_GAUSSIAN_COMMAND",
        "DREAMNAV_REMOTE_DENSE_COMMAND",
        "DREAMNAV_REMOTE_DENSE_BACKEND",
        "DREAMNAV_REMOTE_DENSE_COLMAP_COMMAND",
        "DREAMNAV_REMOTE_DENSE_ALLOW_MOCK_FALLBACK",
        "DREAMNAV_REMOTE_DENSE_RETAINED_JOBS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DREAMNAV_REMOTE_GAUSSIAN_EXECUTABLE", "/opt/dreamnav/gaussian-engine")

    settings = default_settings()

    assert settings.gaussian_command is not None
    assert settings.gaussian_command.endswith("remote_dense_app/gaussian_command_adapter.py")


def test_process_submission_serializes_dense_jobs(tmp_path) -> None:
    settings = RemoteDenseSettings(repo_root=tmp_path, backend="mock")
    app = create_app(settings)
    submissions_root = settings.submissions_root
    job_a = submissions_root / "remote_a"
    job_b = submissions_root / "remote_b"
    job_a.mkdir(parents=True, exist_ok=True)
    job_b.mkdir(parents=True, exist_ok=True)
    bundle_a = job_a / "bundle.zip"
    bundle_b = job_b / "bundle.zip"
    bundle_a.write_bytes(build_bundle_bytes())
    bundle_b.write_bytes(build_bundle_bytes())

    manifest_a = {"job_id": "scene_a", "source_video": "a.mov", "frame_count": 59}
    manifest_b = {"job_id": "scene_b", "source_video": "b.mov", "frame_count": 59}
    semaphore = app.state.job_semaphore
    build_started = Event()
    release_first = Event()
    second_started = Event()
    callback_order: list[str] = []

    def fake_build_dense_result(*args, **kwargs):
        job_root = args[1]
        if job_root == job_a:
            build_started.set()
            release_first.wait(timeout=5)
        else:
            second_started.set()
        return DenseBuildResult(dense_ply=b"ply\nformat ascii 1.0\nend_header\n", backend="mock", warnings=[])

    def fake_callback_sender(*args):
        callback_order.append(args[3])

    thread_a = Thread(
        target=_process_submission,
        args=(
            bundle_a,
            job_a,
            manifest_a,
            "https://example.com/a",
            "token",
            "remote_a",
            settings,
            fake_callback_sender,
            semaphore,
        ),
    )
    thread_b = Thread(
        target=_process_submission,
        args=(
            bundle_b,
            job_b,
            manifest_b,
            "https://example.com/b",
            "token",
            "remote_b",
            settings,
            fake_callback_sender,
            semaphore,
        ),
    )

    with patch("remote_dense_app.main.build_dense_result", side_effect=fake_build_dense_result):
        thread_a.start()
        assert build_started.wait(timeout=5)
        thread_b.start()
        assert not second_started.wait(timeout=0.5)
        release_first.set()
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)

    assert second_started.is_set()
    assert callback_order == ["remote_a", "remote_b"]
    assert loads((job_a / "result.json").read_text(encoding="utf-8"))["status"] == "completed"
    assert loads((job_b / "result.json").read_text(encoding="utf-8"))["status"] == "completed"
