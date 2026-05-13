from io import BytesIO
from json import dumps, loads
from zipfile import ZipFile

from remote_dense_app.generator import bundle_manifest, generate_mock_dense_ply


def test_generate_mock_dense_ply_uses_camera_bundle() -> None:
    bundle_bytes = build_bundle_bytes()

    ply_bytes = generate_mock_dense_ply(bundle_bytes)
    ply_text = ply_bytes.decode("utf-8")

    assert ply_text.startswith("ply\nformat ascii 1.0\n")
    assert "element vertex " in ply_text
    assert ply_text.count("\n") > 1000


def test_bundle_manifest_reads_expected_fields() -> None:
    bundle_bytes = build_bundle_bytes()

    manifest = bundle_manifest(bundle_bytes)

    assert manifest["job_id"] == "scene_abc123"
    assert manifest["frame_count"] == 3


def build_bundle_bytes() -> bytes:
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
