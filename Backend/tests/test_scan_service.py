"""Tests for the scan upload service.

Uses the real Supabase Storage and Postgres — those are already exercised
by test_storage.py. Here we focus on validation logic and the pipeline
contract.

Heavy tests (full upload) are gated behind FEDRETINA_SKIP_STORAGE_TESTS.
"""

from __future__ import annotations

import os
import uuid

import pytest

from fedretina.exceptions import BadRequest, PayloadTooLarge, UnsupportedMediaType
from fedretina.services.scan_service import validate_scan_input


pytestmark = pytest.mark.skipif(
    os.environ.get("FEDRETINA_SKIP_STORAGE_TESTS") == "1",
    reason="Integration tests skipped",
)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def _valid_input(**overrides) -> dict:
    base = {
        "image_bytes": b"\x89PNG\r\n\x1a\n" + b"x" * 2048,
        "original_filename": "fundus.png",
        "file_mime_type": "image/png",
        "patient_mrn": "MRN-88213",
    }
    base.update(overrides)
    return base


def test_validate_accepts_valid_input() -> None:
    result = validate_scan_input(**_valid_input())
    assert result.original_filename == "fundus.png"
    assert result.file_mime_type == "image/png"
    assert result.patient_mrn == "MRN-88213"


def test_validate_normalizes_mime_with_charset() -> None:
    result = validate_scan_input(**_valid_input(file_mime_type="image/jpeg; charset=utf-8"))
    assert result.file_mime_type == "image/jpeg"


def test_validate_rejects_empty_image() -> None:
    with pytest.raises(BadRequest, match="empty"):
        validate_scan_input(**_valid_input(image_bytes=b""))


def test_validate_rejects_tiny_image() -> None:
    with pytest.raises(BadRequest, match="too small"):
        validate_scan_input(**_valid_input(image_bytes=b"abc"))


def test_validate_rejects_oversized_image() -> None:
    with pytest.raises(PayloadTooLarge):
        validate_scan_input(**_valid_input(image_bytes=b"x" * (26 * 1024 * 1024)))


def test_validate_rejects_bad_mime() -> None:
    with pytest.raises(UnsupportedMediaType, match="Unsupported"):
        validate_scan_input(**_valid_input(file_mime_type="application/pdf"))


def test_validate_rejects_short_mrn() -> None:
    with pytest.raises(BadRequest, match="length"):
        validate_scan_input(**_valid_input(patient_mrn="ab"))


def test_validate_rejects_long_mrn() -> None:
    with pytest.raises(BadRequest, match="length"):
        validate_scan_input(**_valid_input(patient_mrn="x" * 200))


def test_validate_rejects_null_byte_in_mrn() -> None:
    with pytest.raises(BadRequest, match="invalid characters"):
        validate_scan_input(**_valid_input(patient_mrn="MRN\x00malicious"))


def test_validate_rejects_empty_filename() -> None:
    with pytest.raises(BadRequest, match="filename"):
        validate_scan_input(**_valid_input(original_filename=""))


# ---------------------------------------------------------------------------
# Full pipeline (integration)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_full_pipeline() -> None:
    """Upload a real scan, verify it lands in DB and storage."""
    from fedretina.db.postgres import close_pool, init_pool
    from fedretina.security.storage import close_storage, delete_encrypted, init_storage
    from fedretina.services.scan_service import process_scan_upload
    from fedretina.db.repositories.scans import fetch_scan_by_id

    await init_pool()
    init_storage()

    # These must match a real user in your profiles table
    clinician_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    # ^ replace with your actual auth user UUID for a real integration test

    # Skip if we don't have a real clinician ID
    from fedretina.db.postgres import get_pool
    pool = get_pool()
    async with pool.acquire() as conn:
        real_user = await conn.fetchval("SELECT id FROM public.profiles LIMIT 1")

    if real_user is None:
        pytest.skip("No profiles exist for integration test")

    clinician_id = real_user

    try:
        response = await process_scan_upload(
            clinician_id=clinician_id,
            clinician_email="test@fedretina.local",
            hospital_node="Node 01",
            image_bytes=b"\x89PNG\r\n\x1a\n" + b"z" * 4096,
            original_filename="integration-test.png",
            file_mime_type="image/png",
            patient_mrn=f"TEST-{uuid.uuid4().hex[:8]}",
            client_ip="127.0.0.1",
        )

        assert response.scan_id is not None
        assert response.status == "encrypted_stored"
        assert response.hospital_node == "Node 01"
        assert response.audit_chain_seq > 0
        assert len(response.sha256_hash) == 64

        # Verify the scans row exists
        row = await fetch_scan_by_id(response.scan_id)
        assert row is not None
        assert row.encrypted_file_path.startswith("Node 01/")

        # Cleanup
        await delete_encrypted(path=response.encrypted_file_path)

    finally:
        close_storage()
        await close_pool()