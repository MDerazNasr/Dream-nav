from pathlib import Path
from zipfile import ZipFile

from app.remote_dense_handoff import (
    RemoteDenseHandoffError,
    build_remote_dense_bundle,
    remote_dense_capabilities_summary,
    remote_submission_payload,
    submit_remote_dense_job,
)


def test_build_remote_dense_bundle_packages_frames_and_camera_artifacts(tmp_path) -> None:
    artifacts_root = tmp_path / "jobs" / "scene_abc123" / "artifacts"
    frames_root = artifacts_root / "frames"
    colmap_sparse_root = artifacts_root / "colmap" / "sparse" / "0"
    frames_root.mkdir(parents=True, exist_ok=True)
    colmap_sparse_root.mkdir(parents=True, exist_ok=True)
    upload_path = tmp_path / "uploads" / "scene_abc123" / "walkthrough.mov"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"video")

    for artifact_name in ("camera_motion.json", "camera_path.json", "frame_extraction.json", "metadata.json"):
        (artifacts_root / artifact_name).write_text("{}", encoding="utf-8")

    for frame_index in range(2):
        (frames_root / f"frame_{frame_index:04d}.jpg").write_bytes(b"\xff\xd8\xff")
    (colmap_sparse_root / "cameras.txt").write_text("# cameras\n", encoding="utf-8")
    (colmap_sparse_root / "images.txt").write_text("# images\n", encoding="utf-8")
    (colmap_sparse_root / "points3D.txt").write_text("# points\n", encoding="utf-8")

    bundle = build_remote_dense_bundle(
        "scene_abc123",
        upload_path,
        artifacts_root,
        "https://dreamnav.example/jobs/scene_abc123/remote-dense-result",
        "callback-secret",
    )

    assert bundle.bundle_file == "remote_dense_bundle.zip"
    assert bundle.frame_count == 2
    assert bundle.bundle_size_bytes > 0
    assert bundle.path.is_file()
    with ZipFile(bundle.path) as archive:
        archive_names = set(archive.namelist())
    assert "frames/frame_0000.jpg" in archive_names
    assert "artifacts/camera_path.json" in archive_names
    assert "artifacts/colmap/sparse/0/cameras.txt" in archive_names
    assert "artifacts/colmap/sparse/0/images.txt" in archive_names
    assert "artifacts/colmap/sparse/0/points3D.txt" in archive_names


def test_submit_remote_dense_job_sends_bundle_and_parses_remote_job_id(tmp_path) -> None:
    bundle_path = tmp_path / "remote_dense_bundle.zip"
    bundle_path.write_bytes(b"zip")
    bundle = build_bundle_stub(bundle_path)
    captured = {}

    class FakeResponse:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"remote_job_id":"remote_001","backend":"mock","warnings":["using fallback"]}'

    def fake_sender(request):
        captured["url"] = request.full_url
        captured["content_type"] = request.headers["Content-type"]
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = request.data
        return FakeResponse()

    result = submit_remote_dense_job(
        "https://dense.example/jobs",
        bundle,
        "callback-secret",
        provider_token="provider-secret",
        sender=fake_sender,
    )

    assert result.remote_job_id == "remote_001"
    assert result.backend == "mock"
    assert result.warnings == ["using fallback"]
    assert captured["url"] == "https://dense.example/jobs"
    assert captured["authorization"] == "Bearer provider-secret"
    assert b'name="callback_token"' in captured["body"]
    assert b"callback-secret" in captured["body"]


def test_build_remote_dense_bundle_requires_frames(tmp_path) -> None:
    artifacts_root = tmp_path / "jobs" / "scene_abc123" / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    upload_path = tmp_path / "uploads" / "scene_abc123" / "walkthrough.mov"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"video")

    for artifact_name in ("camera_motion.json", "camera_path.json", "frame_extraction.json", "metadata.json"):
        (artifacts_root / artifact_name).write_text("{}", encoding="utf-8")

    try:
        build_remote_dense_bundle(
            "scene_abc123",
            upload_path,
            artifacts_root,
            "https://dreamnav.example/jobs/scene_abc123/remote-dense-result",
            "callback-secret",
        )
    except RemoteDenseHandoffError as error:
        assert "extracted JPG frames" in str(error)
    else:
        raise AssertionError("Expected missing-frame bundle creation to fail")


def test_remote_submission_payload_marks_callback_token_configuration(tmp_path) -> None:
    bundle_path = tmp_path / "remote_dense_bundle.zip"
    bundle_path.write_bytes(b"zip")
    payload = remote_submission_payload(
        "scene_abc123",
        submit_remote_dense_job(
            "https://dense.example/jobs",
            build_bundle_stub(bundle_path),
            "callback-secret",
            sender=lambda request: FakeSubmissionResponse(),
        ),
        callback_token_configured=True,
        worker_capabilities=remote_dense_capabilities_summary(
            "https://dense.example/jobs",
            "callback-secret",
            sender=lambda request: FakeCapabilityResponse(),
        ),
    )

    assert payload["job_id"] == "scene_abc123"
    assert payload["callback_token_configured"] is True
    assert payload["worker_capabilities"]["submission_allowed"] is True


def test_remote_dense_capabilities_summary_reads_worker_probe() -> None:
    summary = remote_dense_capabilities_summary(
        "https://dense.example/jobs",
        "callback-secret",
        sender=lambda request: FakeCapabilityResponse(),
    )

    assert summary.provider_url == "https://dense.example/jobs"
    assert summary.submission_allowed is True
    assert summary.real_dense_ready is True
    assert summary.backend == "auto"


def test_remote_dense_capabilities_summary_marks_missing_configuration() -> None:
    summary = remote_dense_capabilities_summary(None, None)

    assert summary.configured is False
    assert summary.submission_allowed is False
    assert "Set DREAMNAV_REMOTE_DENSE_URL to the remote worker jobs endpoint." in summary.missing_requirements
    assert "Set DREAMNAV_REMOTE_DENSE_CALLBACK_TOKEN so the worker can post results back." in summary.missing_requirements


def build_bundle_stub(bundle_path: Path):
    class BundleStub:
        bundle_file = bundle_path.name
        bundle_size_bytes = bundle_path.stat().st_size
        callback_url = "https://dreamnav.example/jobs/scene_abc123/remote-dense-result"
        frame_count = 59
        path = bundle_path
        source_video = "walkthrough.mov"

    return BundleStub()


class FakeSubmissionResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return b'{"remote_job_id":"remote_001","backend":"colmap_dense"}'


class FakeCapabilityResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return (
            b'{"backend":"auto","dense_command":"/opt/dreamnav/dense-adapter",'
            b'"bundled_adapter_available":false,"colmap_command":"/opt/homebrew/bin/colmap",'
            b'"colmap_dense_supported":true,"colmap_dense_reason":null,'
            b'"allow_mock_fallback":true,"retained_job_count":8,'
            b'"real_dense_ready":true,"missing_requirements":[],"warnings":[]}'
        )
