from __future__ import annotations

from dataclasses import dataclass
from json import dumps, loads
from pathlib import Path
from time import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile


class RemoteDenseHandoffError(Exception):
    pass


@dataclass(frozen=True)
class RemoteDenseBundle:
    bundle_file: str
    bundle_size_bytes: int
    callback_url: str
    frame_count: int
    path: Path
    source_video: str


@dataclass(frozen=True)
class RemoteDenseSubmissionResult:
    bundle: RemoteDenseBundle
    provider_url: str
    remote_job_id: str | None
    submission_status: str
    warnings: list[str]


def build_remote_dense_bundle(
    job_id: str,
    upload_path: Path,
    artifacts_root: Path,
    callback_url: str,
    callback_token: str | None,
) -> RemoteDenseBundle:
    frame_paths = sorted((artifacts_root / "frames").glob("*.jpg"))
    if not frame_paths:
        raise RemoteDenseHandoffError("Remote dense handoff requires extracted JPG frames.")

    required_artifacts = [
        "camera_motion.json",
        "camera_path.json",
        "frame_extraction.json",
        "metadata.json",
    ]
    for artifact_name in required_artifacts:
        if not (artifacts_root / artifact_name).is_file():
            raise RemoteDenseHandoffError(f"Remote dense handoff requires {artifact_name}.")

    if not upload_path.is_file():
        raise RemoteDenseHandoffError("Remote dense handoff requires the original uploaded video.")

    bundle_path = artifacts_root / "remote_dense_bundle.zip"
    manifest = {
        "job_id": job_id,
        "source_video": upload_path.name,
        "frame_count": len(frame_paths),
        "callback_url": callback_url,
        "callback_token": callback_token,
    }
    with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", dumps(manifest, indent=2))
        archive.write(upload_path, arcname=f"upload/{upload_path.name}")
        for artifact_name in required_artifacts:
            archive.write(artifacts_root / artifact_name, arcname=f"artifacts/{artifact_name}")
        for frame_path in frame_paths:
            archive.write(frame_path, arcname=f"frames/{frame_path.name}")
        colmap_root = artifacts_root / "colmap"
        if colmap_root.is_dir():
            for path in sorted(colmap_root.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=f"artifacts/colmap/{path.relative_to(colmap_root)}")

    return RemoteDenseBundle(
        bundle_file=bundle_path.name,
        bundle_size_bytes=bundle_path.stat().st_size,
        callback_url=callback_url,
        frame_count=len(frame_paths),
        path=bundle_path,
        source_video=upload_path.name,
    )


def submit_remote_dense_job(
    provider_url: str,
    bundle: RemoteDenseBundle,
    callback_token: str | None,
    provider_token: str | None = None,
    sender=urlopen,
) -> RemoteDenseSubmissionResult:
    fields = {
        "job_id": bundle.path.parent.parent.name,
        "callback_url": bundle.callback_url,
        "callback_token": callback_token or "",
        "source_video": bundle.source_video,
    }
    body, content_type = _multipart_body(fields, bundle.path)
    headers = {"Content-Type": content_type}
    if provider_token:
        headers["Authorization"] = f"Bearer {provider_token}"

    request = Request(provider_url, data=body, headers=headers, method="POST")
    try:
        with sender(request) as response:
            status_code = getattr(response, "status", None) or response.getcode()
            payload = response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RemoteDenseHandoffError(f"Remote dense provider rejected the submission: {detail or error.reason}") from error
    except URLError as error:
        raise RemoteDenseHandoffError(f"Remote dense provider is unavailable: {error.reason}") from error

    if status_code < 200 or status_code >= 300:
        raise RemoteDenseHandoffError(f"Remote dense provider returned HTTP {status_code}.")

    remote_job_id = _remote_job_id(payload)
    return RemoteDenseSubmissionResult(
        bundle=bundle,
        provider_url=provider_url,
        remote_job_id=remote_job_id,
        submission_status="submitted",
        warnings=[],
    )


def callback_warnings(public_api_base_url: str | None) -> list[str]:
    if public_api_base_url:
        return []

    return ["Using the current request host for the remote callback URL. Set DREAMNAV_PUBLIC_API_BASE_URL if the remote worker cannot reach this API directly."]


def remote_submission_payload(
    job_id: str,
    result: RemoteDenseSubmissionResult,
    callback_token_configured: bool,
) -> dict[str, object]:
    return {
        "job_id": job_id,
        "provider_url": result.provider_url,
        "remote_job_id": result.remote_job_id,
        "submission_status": result.submission_status,
        "bundle_file": result.bundle.bundle_file,
        "bundle_size_bytes": result.bundle.bundle_size_bytes,
        "frame_count": result.bundle.frame_count,
        "source_video": result.bundle.source_video,
        "callback_url": result.bundle.callback_url,
        "callback_token_configured": callback_token_configured,
        "warnings": result.warnings,
        "submitted_at_sec": int(time()),
    }


def _multipart_body(fields: dict[str, str], bundle_path: Path) -> tuple[bytes, str]:
    boundary = f"dreamnav-{uuid4().hex}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="bundle"; filename="{bundle_path.name}"\r\n'.encode("utf-8")
    )
    body.extend(b"Content-Type: application/zip\r\n\r\n")
    body.extend(bundle_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def _remote_job_id(payload: bytes) -> str | None:
    if not payload:
        return None

    try:
        data = loads(payload.decode("utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    for field_name in ("remote_job_id", "job_id", "submission_id"):
        value = data.get(field_name)
        if isinstance(value, str) and value:
            return value

    return None
