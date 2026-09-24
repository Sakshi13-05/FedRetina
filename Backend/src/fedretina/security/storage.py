"""
This Python file (storage.py) is the actual implementation of the storage system. 
It takes the concepts of the database policies, the Pydantic data models,
 and the strict deletion rules, and turns them into working code.

"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from supabase import Client, create_client
from typing import Any

from fedretina.config import get_settings
from fedretina.exceptions import BadRequest, StorageError
from fedretina.logging import get_logger
from fedretina.schemas.storage import DownloadResult, SignedUrl, UploadResult
from fedretina.security.crypto import sha256_hex

log = get_logger("security.storage")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_ALLOWED_NODES = frozenset({"Node 01", "Node 02", "Node 03"})
_SIGNED_URL_DEFAULT_TTL_SECONDS = 300  # 5 minutes
_SIGNED_URL_MAX_TTL_SECONDS = 3600     # hard cap: 1 hour


# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_client: Client | None = None


# ---------------------------------------------------------------------------
# Initialization / lifecycle
# ---------------------------------------------------------------------------
def init_storage() -> Client:
    """Initialize the module-level Supabase Storage client.

    Idempotent. Reads URL + service-role key from settings.
    """
    global _client

    if _client is not None:
        return _client

    settings = get_settings()

    log.info(
        "storage.init.begin",
        extra={"bucket": settings.supabase_scans_bucket},
    )

    try:
        client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key.get_secret_value(),
        )
    except Exception as exc:
        log.exception("storage.init.failed")
        raise StorageError("Failed to initialize Supabase client") from exc

    _client = client
    log.info("storage.init.ready")
    return _client


def get_storage() -> Client:
    """Return the initialized Supabase client."""
    if _client is None:
        raise RuntimeError(
            "Storage client is not initialized. "
            "Ensure init_storage() ran during application startup."
        )
    return _client


def close_storage() -> None:
    """Release the storage client. Idempotent."""
    global _client
    if _client is None:
        return
    log.info("storage.close.begin")
    # supabase-py does not expose an explicit close; the httpx client
    # inside it will be garbage collected. We drop our reference and
    # clear the module state so a fresh init can be performed if needed.
    _client = None
    log.info("storage.close.complete")


# ---------------------------------------------------------------------------
# Path generation
# ---------------------------------------------------------------------------
def build_storage_path(
    *,
    hospital_node: str,
    scan_id: UUID,
    when: datetime | None = None,
) -> str:
    """Build the  storage path for an encrypted scan.

    Format: {hospital_node}/{yyyy}/{mm}/{scan_uuid}.enc

    Args:
        hospital_node: One of "Node 01", "Node 02", "Node 03".
        scan_id: UUID of the scan; becomes the filename.
        when: Upload timestamp; defaults to now (UTC). Only the year and
            month are used in the path.

    Returns:
        Path string, e.g. "Node 01/2026/09/7c9e6679-7425-40de-944b-e07fc1f90ae7.enc"

    Raises:
        BadRequest: if hospital_node is not a known node or scan_id is invalid.
    """
    if hospital_node not in _ALLOWED_NODES:
        raise BadRequest(
            f"Unknown hospital node: {hospital_node!r}",
            context={"allowed": sorted(_ALLOWED_NODES)},
        )
    if not isinstance(scan_id, UUID):
        raise BadRequest("scan_id must be a UUID")

    ts = when or datetime.now(timezone.utc)
    return f"{hospital_node}/{ts.year:04d}/{ts.month:02d}/{scan_id}.enc"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
async def upload_encrypted(
    *,
    path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> UploadResult:
    """Upload encrypted bytes to Supabase Storage.

    Args:
        path: Full path within the bucket (see build_storage_path).
        data: Ciphertext bytes to store. Must not be empty.
        content_type: MIME type. Defaults to application/octet-stream
            (matches the bucket's allowed MIME list).

    Returns:
        UploadResult with the path, size, and computed SHA-256.

    Raises:
        BadRequest: if path or data is invalid.
        StorageError: if the upload fails.
    """
    if not path or "/" not in path:
        raise BadRequest("path must be of the form <node>/<yyyy>/<mm>/<uuid>.enc")
    if not data:
        raise BadRequest("data must not be empty")

    settings = get_settings()
    bucket = settings.supabase_scans_bucket
    client = get_storage()

    def _do_upload() -> None:
        client.storage.from_(bucket).upload(
            path=path,
            file=data,
            file_options={"content-type": content_type, "upsert": "false"},
        )

    log.info(
        "storage.upload.begin",
        extra={"bucket": bucket, "path": path, "size_bytes": len(data)},
    )

    try:
        await asyncio.to_thread(_do_upload)
    except Exception as exc:
        # Supabase raises a variety of exceptions; normalize to StorageError.
        log.exception("storage.upload.failed", extra={"path": path})
        raise StorageError("Failed to upload object") from exc

    digest = sha256_hex(data)

    log.info(
        "storage.upload.ready",
        extra={"path": path, "size_bytes": len(data), "sha256": digest[:16]},
    )

    return UploadResult(
        path=path,
        bucket=bucket,
        size_bytes=len(data),
        sha256_hex=digest,
        uploaded_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
async def download_encrypted(*, path: str) -> DownloadResult:
    """Download encrypted bytes from Supabase Storage.

    Args:
        path: Full path within the bucket.

    Returns:
        DownloadResult containing the raw ciphertext bytes.

    Raises:
        BadRequest: if path is invalid.
        StorageError: if the download fails.
    """
    if not path or "/" not in path:
        raise BadRequest("path must be of the form <node>/<yyyy>/<mm>/<uuid>.enc")

    settings = get_settings()
    bucket = settings.supabase_scans_bucket
    client = get_storage()

    def _do_download() -> bytes:
        return client.storage.from_(bucket).download(path)

    log.info("storage.download.begin", extra={"bucket": bucket, "path": path})

    try:
        raw: bytes = await asyncio.to_thread(_do_download)
    except Exception as exc:
        log.exception("storage.download.failed", extra={"path": path})
        raise StorageError("Failed to download object") from exc

    if not isinstance(raw, (bytes, bytearray)):
        raise StorageError("Storage returned unexpected payload type")

    data = bytes(raw)

    log.info(
        "storage.download.ready",
        extra={"path": path, "size_bytes": len(data)},
    )

    return DownloadResult(path=path, data=data, size_bytes=len(data))


# ---------------------------------------------------------------------------
# Signed URLs
# ---------------------------------------------------------------------------
async def create_signed_url(
    *,
    path: str,
    expires_in_seconds: int = _SIGNED_URL_DEFAULT_TTL_SECONDS,
) -> SignedUrl:
    """Create a time-limited signed URL for reading an object.

    Args:
        path: Full path within the bucket.
        expires_in_seconds: Validity period. Clamped to [1, 3600].

    Returns:
        SignedUrl with the URL, path, and expiry timestamp.

    Raises:
        BadRequest: if path is invalid.
        StorageError: if the signing call fails.
    """
    if not path or "/" not in path:
        raise BadRequest("path must be of the form <node>/<yyyy>/<mm>/<uuid>.enc")

    if expires_in_seconds <= 0:
        raise BadRequest("expires_in_seconds must be positive")
    if expires_in_seconds > _SIGNED_URL_MAX_TTL_SECONDS:
        expires_in_seconds = _SIGNED_URL_MAX_TTL_SECONDS

    settings = get_settings()
    bucket = settings.supabase_scans_bucket
    client = get_storage()

    # Change -> dict to -> Any
    def _do_sign() -> Any:
        return client.storage.from_(bucket).create_signed_url(
            path, expires_in_seconds
        )

    log.info(
        "storage.sign_url.begin",
        extra={"path": path, "expires_in": expires_in_seconds},
    )

    try:
        # Change result: dict to result: Any
        result: Any = await asyncio.to_thread(_do_sign)
    except Exception as exc:
        log.exception("storage.sign_url.failed", extra={"path": path})
        raise StorageError("Failed to create signed URL") from exc

    # supabase-py returns either {"signedURL": "..."} (v2.x) or
    # {"signedUrl": "..."} depending on version. Handle both.
    url = result.get("signedURL") or result.get("signedUrl")
    if not url:
        raise StorageError("Storage returned an empty signed URL")

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

    log.info("storage.sign_url.ready", extra={"path": path})

    return SignedUrl(url=url, path=path, expires_at=expires_at)


# ---------------------------------------------------------------------------
# Delete (backend-only; no HTTP endpoint exposes this)
# ---------------------------------------------------------------------------
async def delete_encrypted(*, path: str) -> None:
    """Delete an object from Supabase Storage.

    Backend-only. Must be preceded by an audit_logs entry recording the
    deletion. Never expose this to a clinician-facing HTTP route.

    Args:
        path: Full path within the bucket.

    Raises:
        BadRequest: if path is invalid.
        StorageError: if the delete fails.
    """
    if not path or "/" not in path:
        raise BadRequest("path must be of the form <node>/<yyyy>/<mm>/<uuid>.enc")

    settings = get_settings()
    bucket = settings.supabase_scans_bucket
    client = get_storage()

    def _do_delete() -> None:
        client.storage.from_(bucket).remove([path])

    log.warning("storage.delete.begin", extra={"path": path})

    try:
        await asyncio.to_thread(_do_delete)
    except Exception as exc:
        log.exception("storage.delete.failed", extra={"path": path})
        raise StorageError("Failed to delete object") from exc

    log.warning("storage.delete.ready", extra={"path": path})