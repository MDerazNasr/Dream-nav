from __future__ import annotations

from dataclasses import dataclass
from json import dumps, loads
from pathlib import Path
from time import time
import httpx
from urllib.parse import urlsplit, urlunsplit
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
    backend: str | None
    warnings: list[str]


@dataclass(frozen=True)
class RemoteDenseCapabilitiesSummary:
    provider_url: str | None
    configured: bool
    callback_token_configured: bool
    backend: str | None
    dense_command: str | None
    bundled_adapter_available: bool
    colmap_command: str | None
    colmap_dense_supported: bool
    colmap_dense_reason: str | None
    allow_mock_fallback: bool
    retained_job_count: int
    real_dense_ready: bool
    submission_allowed: bool
    missing_requirements: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class RemoteDenseJobStatusSummary:
    job_id: str
    remote_job_id: str | None
    status: str
    backend: str | None
    source_video: str | None
    frame_count: int | None
    warnings: list[str]
    error: str | None


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
    sender=None,
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

    if sender is None:
        status_code, payload = _httpx_request(
            "POST",
            provider_url,
            headers=headers,
            content=body,
            error_prefix="Remote dense provider",
            timeout_sec=95.0,
        )
    else:
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
        backend=_string_field(response_payload(payload), "backend"),
        warnings=_string_list_field(response_payload(payload), "warnings"),
    )


def callback_warnings(public_api_base_url: str | None) -> list[str]:
    if public_api_base_url:
        return []

    return ["Using the current request host for the remote callback URL. Set DREAMNAV_PUBLIC_API_BASE_URL if the remote worker cannot reach this API directly."]


def remote_dense_capabilities_summary(
    provider_url: str | None,
    callback_token: str | None,
    provider_token: str | None = None,
    sender=None,
) -> RemoteDenseCapabilitiesSummary:
    missing_requirements: list[str] = []
    warnings: list[str] = []
    callback_token_configured = bool(callback_token)
    configured = bool(provider_url and callback_token_configured)

    if not provider_url:
        missing_requirements.append("Set DREAMNAV_REMOTE_DENSE_URL to the remote worker jobs endpoint.")
    if not callback_token_configured:
        missing_requirements.append("Set DREAMNAV_REMOTE_DENSE_CALLBACK_TOKEN so the worker can post results back.")

    if not provider_url:
        return RemoteDenseCapabilitiesSummary(
            provider_url=None,
            configured=False,
            callback_token_configured=callback_token_configured,
            backend=None,
            dense_command=None,
            bundled_adapter_available=False,
            colmap_command=None,
            colmap_dense_supported=False,
            colmap_dense_reason=None,
            allow_mock_fallback=False,
            retained_job_count=0,
            real_dense_ready=False,
            submission_allowed=False,
            missing_requirements=missing_requirements,
            warnings=warnings,
        )

    capability_headers = {"Authorization": f"Bearer {provider_token}"} if provider_token else None
    if sender is None:
        status_code, payload = _httpx_request(
            "GET",
            _capabilities_url(provider_url),
            headers=capability_headers,
            error_prefix="Remote dense worker capability probe",
            timeout_sec=30.0,
        )
    else:
        request = Request(_capabilities_url(provider_url), method="GET")
        if provider_token:
            request.add_header("Authorization", f"Bearer {provider_token}")

        try:
            with sender(request) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                payload = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RemoteDenseHandoffError(
                f"Remote dense worker capability probe failed: {detail or error.reason}"
            ) from error
        except URLError as error:
            raise RemoteDenseHandoffError(f"Remote dense worker capability probe failed: {error.reason}") from error

    if status_code < 200 or status_code >= 300:
        raise RemoteDenseHandoffError(f"Remote dense worker capability probe returned HTTP {status_code}.")

    data = response_payload(payload)
    if data is None:
        raise RemoteDenseHandoffError("Remote dense worker capability probe returned an invalid response.")

    backend = _string_field(data, "backend")
    dense_command = _string_field(data, "dense_command")
    bundled_adapter_available = _bool_field(data, "bundled_adapter_available")
    colmap_command = _string_field(data, "colmap_command")
    colmap_dense_supported = _bool_field(data, "colmap_dense_supported")
    colmap_dense_reason = _string_field(data, "colmap_dense_reason")
    allow_mock_fallback = _bool_field(data, "allow_mock_fallback")
    retained_job_count = _int_field(data, "retained_job_count")
    real_dense_ready = _bool_field(data, "real_dense_ready")
    warnings.extend(_string_list_field(data, "warnings"))
    missing_requirements.extend(_string_list_field(data, "missing_requirements"))
    submission_allowed = configured and real_dense_ready
    if configured and not real_dense_ready and not missing_requirements:
        missing_requirements.append("Run the worker on a machine that can execute a real dense reconstruction backend.")

    return RemoteDenseCapabilitiesSummary(
        provider_url=provider_url,
        configured=configured,
        callback_token_configured=callback_token_configured,
        backend=backend,
        dense_command=dense_command,
        bundled_adapter_available=bundled_adapter_available,
        colmap_command=colmap_command,
        colmap_dense_supported=colmap_dense_supported,
        colmap_dense_reason=colmap_dense_reason,
        allow_mock_fallback=allow_mock_fallback,
        retained_job_count=retained_job_count,
        real_dense_ready=real_dense_ready,
        submission_allowed=submission_allowed,
        missing_requirements=missing_requirements,
        warnings=warnings,
    )


def remote_submission_payload(
    job_id: str,
    result: RemoteDenseSubmissionResult,
    callback_token_configured: bool,
    worker_capabilities: RemoteDenseCapabilitiesSummary,
) -> dict[str, object]:
    return {
        "job_id": job_id,
        "provider_url": result.provider_url,
        "remote_job_id": result.remote_job_id,
        "submission_status": result.submission_status,
        "backend": result.backend,
        "bundle_file": result.bundle.bundle_file,
        "bundle_size_bytes": result.bundle.bundle_size_bytes,
        "frame_count": result.bundle.frame_count,
        "source_video": result.bundle.source_video,
        "callback_url": result.bundle.callback_url,
        "callback_token_configured": callback_token_configured,
        "worker_capabilities": remote_dense_capabilities_payload(worker_capabilities),
        "warnings": result.warnings,
        "submitted_at_sec": int(time()),
    }


def remote_dense_capabilities_payload(summary: RemoteDenseCapabilitiesSummary) -> dict[str, object]:
    return {
        "provider_url": summary.provider_url,
        "configured": summary.configured,
        "callback_token_configured": summary.callback_token_configured,
        "backend": summary.backend,
        "dense_command": summary.dense_command,
        "bundled_adapter_available": summary.bundled_adapter_available,
        "colmap_command": summary.colmap_command,
        "colmap_dense_supported": summary.colmap_dense_supported,
        "colmap_dense_reason": summary.colmap_dense_reason,
        "allow_mock_fallback": summary.allow_mock_fallback,
        "retained_job_count": summary.retained_job_count,
        "real_dense_ready": summary.real_dense_ready,
        "submission_allowed": summary.submission_allowed,
        "missing_requirements": summary.missing_requirements,
        "warnings": summary.warnings,
    }


def remote_dense_job_status(
    provider_url: str,
    remote_job_id: str,
    provider_token: str | None = None,
) -> RemoteDenseJobStatusSummary:
    status_code, payload = _httpx_request(
        "GET",
        _remote_job_status_url(provider_url, remote_job_id),
        headers={"Authorization": f"Bearer {provider_token}"} if provider_token else None,
        error_prefix="Remote dense worker status probe",
        timeout_sec=30.0,
    )

    if status_code < 200 or status_code >= 300:
        raise RemoteDenseHandoffError(f"Remote dense worker status probe returned HTTP {status_code}.")

    data = response_payload(payload)
    if data is None:
        raise RemoteDenseHandoffError("Remote dense worker status probe returned an invalid response.")

    frame_count = data.get("frame_count")
    return RemoteDenseJobStatusSummary(
        job_id=_string_field(data, "job_id") or remote_job_id,
        remote_job_id=remote_job_id,
        status=_string_field(data, "status") or "submitted",
        backend=_string_field(data, "backend"),
        source_video=_string_field(data, "source_video"),
        frame_count=frame_count if isinstance(frame_count, int) and frame_count >= 0 else None,
        warnings=_string_list_field(data, "warnings"),
        error=_string_field(data, "error"),
    )


def remote_dense_job_status_payload(summary: RemoteDenseJobStatusSummary) -> dict[str, object]:
    return {
        "job_id": summary.job_id,
        "remote_job_id": summary.remote_job_id,
        "status": summary.status,
        "backend": summary.backend,
        "source_video": summary.source_video,
        "frame_count": summary.frame_count,
        "warnings": summary.warnings,
        "error": summary.error,
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
    data = response_payload(payload)
    if data is None:
        return None

    for field_name in ("remote_job_id", "job_id", "submission_id"):
        value = data.get(field_name)
        if isinstance(value, str) and value:
            return value

    return None


def response_payload(payload: bytes) -> dict[str, object] | None:
    if not payload:
        return None

    try:
        data = loads(payload.decode("utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    return data


def _string_field(payload: dict[str, object] | None, field_name: str) -> str | None:
    if payload is None:
        return None

    value = payload.get(field_name)
    return value if isinstance(value, str) and value else None


def _string_list_field(payload: dict[str, object] | None, field_name: str) -> list[str]:
    if payload is None:
        return []

    value = payload.get(field_name)
    if not isinstance(value, list):
        return []

    return [entry for entry in value if isinstance(entry, str) and entry]


def _bool_field(payload: dict[str, object], field_name: str) -> bool:
    value = payload.get(field_name)
    return value if isinstance(value, bool) else False


def _int_field(payload: dict[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    return value if isinstance(value, int) and value >= 0 else 0


def _capabilities_url(provider_url: str) -> str:
    split_url = urlsplit(provider_url)
    path = split_url.path.rstrip("/")
    capability_path = f"{path.rsplit('/', 1)[0] if path.endswith('/jobs') else path}/capabilities"
    return urlunsplit((split_url.scheme, split_url.netloc, capability_path, "", ""))


def _remote_job_status_url(provider_url: str, remote_job_id: str) -> str:
    split_url = urlsplit(provider_url)
    path = split_url.path.rstrip("/")
    jobs_path = path if path.endswith("/jobs") else f"{path}/jobs"
    return urlunsplit((split_url.scheme, split_url.netloc, f"{jobs_path}/{remote_job_id}", "", ""))


def _httpx_request(
    method: str,
    url: str,
    headers: dict[str, str] | None,
    error_prefix: str,
    content: bytes | None = None,
    timeout_sec: float = 30.0,
) -> tuple[int, bytes]:
    try:
        response = httpx.request(method, url, headers=headers, content=content, timeout=timeout_sec)
    except httpx.HTTPError as error:
        raise RemoteDenseHandoffError(f"{error_prefix} is unavailable: {error}") from error

    if response.status_code < 200 or response.status_code >= 300:
        detail = response.text.strip()
        raise RemoteDenseHandoffError(
            f"{error_prefix} rejected the request: {detail or f'HTTP {response.status_code}'}"
        )

    return response.status_code, response.content
