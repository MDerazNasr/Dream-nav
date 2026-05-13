from remote_dense_app.generator import bundle_manifest, generate_mock_dense_ply
from test_helpers import build_bundle_bytes


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
