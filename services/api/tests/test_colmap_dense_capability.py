from pathlib import Path

from app.colmap_dense_capability import detect_colmap_dense_stereo_support


def test_detect_colmap_dense_stereo_support_reports_cuda_less_build(tmp_path: Path) -> None:
    fake_colmap = tmp_path / "fake_colmap.py"
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "if sys.argv[1:] == ['patch_match_stereo', '-h']:\n"
        "    print('COLMAP 4.0.4 without CUDA')\n",
        encoding="utf-8",
    )
    fake_colmap.chmod(0o755)

    supported, reason = detect_colmap_dense_stereo_support(str(fake_colmap))

    assert supported is False
    assert reason == "The installed COLMAP build does not support dense stereo on this machine."


def test_detect_colmap_dense_stereo_support_reports_supported_build(tmp_path: Path) -> None:
    fake_colmap = tmp_path / "fake_colmap.py"
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "if sys.argv[1:] == ['patch_match_stereo', '-h']:\n"
        "    print('COLMAP 4.0.4 with CUDA')\n",
        encoding="utf-8",
    )
    fake_colmap.chmod(0o755)

    supported, reason = detect_colmap_dense_stereo_support(str(fake_colmap))

    assert supported is True
    assert reason is None
