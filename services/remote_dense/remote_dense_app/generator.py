from __future__ import annotations

from io import BytesIO
from json import loads
from math import cos, sin, tau
from pathlib import Path
from shutil import rmtree
from zipfile import ZipFile


class RemoteDenseGenerationError(Exception):
    pass


def bundle_manifest(bundle_bytes: bytes) -> dict[str, object]:
    try:
        with ZipFile(BytesIO(bundle_bytes)) as archive:
            return loads(archive.read("manifest.json").decode("utf-8"))
    except Exception as error:
        raise RemoteDenseGenerationError("Remote dense bundle is invalid.") from error


def extract_bundle(bundle_path: Path, extracted_root: Path) -> None:
    if extracted_root.exists():
        rmtree(extracted_root)
    extracted_root.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(bundle_path) as archive:
            archive.extractall(extracted_root)
    except Exception as error:
        raise RemoteDenseGenerationError("Remote dense bundle could not be extracted.") from error


def generate_mock_dense_ply(bundle_bytes: bytes) -> bytes:
    try:
        with ZipFile(BytesIO(bundle_bytes)) as archive:
            camera_path = loads(archive.read("artifacts/camera_path.json").decode("utf-8"))
            frame_names = [name for name in archive.namelist() if name.startswith("frames/") and name.endswith(".jpg")]
    except Exception as error:
        raise RemoteDenseGenerationError("Remote dense bundle is missing camera artifacts.") from error

    return _mock_dense_ply_from_camera_path(camera_path, len(frame_names))


def generate_mock_dense_ply_from_extracted(extracted_root: Path) -> bytes:
    try:
        camera_path = loads((extracted_root / "artifacts" / "camera_path.json").read_text(encoding="utf-8"))
        frame_names = list((extracted_root / "frames").glob("*.jpg"))
    except Exception as error:
        raise RemoteDenseGenerationError("Extracted remote dense bundle is missing camera artifacts.") from error

    return _mock_dense_ply_from_camera_path(camera_path, len(frame_names))


def _mock_dense_ply_from_camera_path(camera_path: dict[str, object], frame_count: int) -> bytes:
    poses = camera_path.get("poses")
    if not isinstance(poses, list) or not poses:
        raise RemoteDenseGenerationError("Remote dense bundle did not include camera poses.")

    frame_count = max(1, frame_count)
    points = []
    ring_samples = max(64, min(192, frame_count * 8))
    floor_extent = min(4.5, 2.2 + (frame_count * 0.05))

    for pose_index, pose in enumerate(poses):
        position = pose.get("position") if isinstance(pose, dict) else None
        if not isinstance(position, list) or len(position) != 3:
            continue

        px, py, pz = (float(position[0]), float(position[1]), float(position[2]))
        radius = 0.25 + (pose_index % 3) * 0.04
        for sample_index in range(ring_samples):
            angle = tau * sample_index / ring_samples
            points.append(
                (
                    px + cos(angle) * radius,
                    py - 0.15 + sin(angle) * 0.18,
                    pz - 0.55 + sin(angle * 0.5) * 0.12,
                    214,
                    226,
                    235,
                )
            )

        for column_index in range(6):
            offset = -0.45 + column_index * 0.18
            points.append((px + offset, py - 0.9, pz - 0.4, 136, 156, 169))
            points.append((px + offset, py - 0.3, pz - 0.7, 181, 196, 206))

    floor_step = 0.09
    floor_cells = int((floor_extent * 2) / floor_step)
    for x_index in range(floor_cells + 1):
        for z_index in range(floor_cells + 1):
            x = -floor_extent + x_index * floor_step
            z = -floor_extent + z_index * floor_step
            shade = 96 + ((x_index + z_index) % 4) * 12
            points.append((x, 0.0, z, shade, shade + 14, shade + 22))

    return point_cloud_ply(points)


def point_cloud_ply(points: list[tuple[float, float, float, int, int, int]]) -> bytes:
    rows = "\n".join(
        f"{x:.4f} {y:.4f} {z:.4f} {red} {green} {blue}"
        for x, y, z, red, green, blue in points
    )
    return (
        "ply\n"
        "format ascii 1.0\n"
        f"element vertex {len(points)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
        f"{rows}\n"
    ).encode("utf-8")


def write_submission_bundle(root: Path, remote_job_id: str, bundle_bytes: bytes) -> Path:
    job_root = root / remote_job_id
    if job_root.exists():
        rmtree(job_root)
    job_root.mkdir(parents=True, exist_ok=True)
    bundle_path = job_root / "bundle.zip"
    bundle_path.write_bytes(bundle_bytes)
    return bundle_path
