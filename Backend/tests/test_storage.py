"""Tests for the Supabase Storage client.

These tests hit the REAL Supabase Storage (the fedretina-scans bucket).
They use the service_role key, so they bypass RLS — they test the client
wrapper, not the policies.

Set FEDRETINA_SKIP_STORAGE_TESTS=1 to skip these in CI environments
that lack network access.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Generator

import pytest

from fedretina.exceptions import BadRequest, StorageError
from fedretina.security.storage import (
    build_storage_path,
    close_storage,
    create_signed_url,
    delete_encrypted,
    download_encrypted,
    init_storage,
    upload_encrypted,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("FEDRETINA_SKIP_STORAGE_TESTS") == "1",
    reason="Storage tests skipped (FEDRETINA_SKIP_STORAGE_TESTS=1)",
)


@pytest.fixture(autouse=True)
def _storage_client():
    """Ensure the storage client is initialized for each test.

    Function-scoped (not module-scoped) so pytest-asyncio's event loop
    handling doesn't drop the module-level client between tests.
    """
    from fedretina.security import storage as storage_module

    # Force re-init if a prior test cleaned up
    if storage_module._client is None:
        init_storage()

    yield

    # Do NOT close between tests — closing and reopening per test
    # triggers connection churn against Supabase. Module cleanup
    # happens naturally when the process exits.


# ---------------------------------------------------------------------------
# Path construction
# ---------------------------------------------------------------------------
def test_build_path_format() -> None:
    scan_id = uuid.uuid4()
    path = build_storage_path(
        hospital_node="Node 01",
        scan_id=scan_id,
        when=datetime(2026, 9, 24, tzinfo=timezone.utc),
    )
    assert path == f"Node 01/2026/09/{scan_id}.enc"


def test_build_path_zero_pads_month() -> None:
    scan_id = uuid.uuid4()
    path = build_storage_path(
        hospital_node="Node 02",
        scan_id=scan_id,
        when=datetime(2026, 3, 5, tzinfo=timezone.utc),
    )
    assert "/2026/03/" in path


def test_build_path_rejects_unknown_node() -> None:
    with pytest.raises(BadRequest, match="Unknown hospital node"):
        build_storage_path(hospital_node="Node 99", scan_id=uuid.uuid4())


def test_build_path_rejects_non_uuid() -> None:
    with pytest.raises(BadRequest, match="scan_id must be a UUID"):
        build_storage_path(
            hospital_node="Node 01",
            scan_id="not-a-uuid",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Round-trip upload/download
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_upload_download_roundtrip() -> None:
    scan_id = uuid.uuid4()
    path = build_storage_path(hospital_node="Node 01", scan_id=scan_id)
    payload = b"\x00\x01\x02\x03ciphertext bytes for storage round-trip test"

    uploaded = await upload_encrypted(path=path, data=payload)
    assert uploaded.path == path
    assert uploaded.size_bytes == len(payload)
    assert len(uploaded.sha256_hex) == 64

    try:
        fetched = await download_encrypted(path=path)
        assert fetched.data == payload
        assert fetched.size_bytes == len(payload)
    finally:
        await delete_encrypted(path=path)


@pytest.mark.asyncio
async def test_upload_empty_data_rejected() -> None:
    scan_id = uuid.uuid4()
    path = build_storage_path(hospital_node="Node 01", scan_id=scan_id)
    with pytest.raises(BadRequest, match="must not be empty"):
        await upload_encrypted(path=path, data=b"")


@pytest.mark.asyncio
async def test_upload_bad_path_rejected() -> None:
    with pytest.raises(BadRequest, match="path must be of the form"):
        await upload_encrypted(path="no-slashes.enc", data=b"x")


# ---------------------------------------------------------------------------
# Signed URLs
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_signed_url() -> None:
    scan_id = uuid.uuid4()
    path = build_storage_path(hospital_node="Node 01", scan_id=scan_id)
    payload = b"signed-url-test-payload"

    await upload_encrypted(path=path, data=payload)
    try:
        signed = await create_signed_url(path=path, expires_in_seconds=60)
        assert signed.path == path
        assert signed.url.startswith("https://")
        assert signed.expires_at > datetime.now(timezone.utc)
    finally:
        await delete_encrypted(path=path)


@pytest.mark.asyncio
async def test_signed_url_clamps_excessive_ttl() -> None:
    scan_id = uuid.uuid4()
    path = build_storage_path(hospital_node="Node 01", scan_id=scan_id)
    payload = b"clamp-test"

    await upload_encrypted(path=path, data=payload)
    try:
        signed = await create_signed_url(path=path, expires_in_seconds=999_999)
        delta = (signed.expires_at - datetime.now(timezone.utc)).total_seconds()
        assert 3500 < delta <= 3600
    finally:
        await delete_encrypted(path=path)


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_download_missing_object() -> None:
    path = f"Node 01/2026/09/{uuid.uuid4()}.enc"
    with pytest.raises(StorageError):
        await download_encrypted(path=path)


@pytest.mark.asyncio
async def test_delete_missing_object_is_idempotent() -> None:
    # Supabase remove() is idempotent — deleting a nonexistent object
    # doesn't error. This test documents that behavior.
    path = f"Node 01/2026/09/{uuid.uuid4()}.enc"
    await delete_encrypted(path=path)
