from __future__ import annotations

from io import BytesIO
from json import dumps
from zipfile import ZipFile


def build_bundle_bytes(include_colmap_sparse: bool = False) -> bytes:
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
                    ],
                }
            ),
        )
        archive.writestr("artifacts/camera_motion.json", "{}")
        archive.writestr("artifacts/frame_extraction.json", "{}")
        archive.writestr("artifacts/metadata.json", "{}")
        archive.writestr("frames/frame_0000.jpg", b"\xff\xd8\xff")
        archive.writestr("frames/frame_0001.jpg", b"\xff\xd8\xff")
        archive.writestr("frames/frame_0002.jpg", b"\xff\xd8\xff")
        if include_colmap_sparse:
            archive.writestr("artifacts/colmap/sparse/0/cameras.txt", "# cameras\n")
            archive.writestr("artifacts/colmap/sparse/0/images.txt", "# images\n")
            archive.writestr("artifacts/colmap/sparse/0/points3D.txt", "# points\n")
    return buffer.getvalue()
