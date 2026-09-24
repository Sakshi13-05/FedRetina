"""Scan upload service — orchestrates the full encryption and storage pipeline.

This is where Sub-Tasks 3, 4, 5, 6, 7 come together. The service:

    1. Validates the input
    2. Pseudonymizes the patient MRN (HMAC)
    3. Encrypts the image (AES-256-GCM)
    4. Uploads the encrypted blob to Supabase Storage
    5. Writes the scans row
    6. Writes the audit_logs row
    7. Returns the response

Compensating action: if step 6 fails after step 5 succeeded, we
attempt to delete the uploaded blob. If that also fails, we log a
CRITICAL alert and let the audit trail reflect the anomaly.

The service has no HTTP concerns. It takes a CurrentUser and raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from fedretina.db.repositories.audit import append_audit_event
from fedretina.db.repositories.scans import ScanRow, insert_scan
from fedretina.exceptions import (
    BadRequest,
    PayloadTooLarge,
    StorageError,
    UnsupportedMediaType,
)
from fedretina.logging import get_logger
from fedretina.schemas.scan import ScanUploadResponse
from fedretina.security.crypto import (
    EncryptedBlob,
    KeyProvider,
    encrypt,
    sha256_hex,
)
from fedretina.security.storage import (
    build_storage_path,
    delete_encrypted,
    upload_encrypted,
)

log = get_logger("services.scan")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "image/bmp",
    "image/webp",
})
_MIN_IMAGE_BYTES = 1_024                # 1 KB minimum
_MAX_IMAGE_BYTES = 25 * 1024 * 1024     # 25 MB hard cap
_MIN_MRN_LEN = 3
_MAX_MRN_LEN = 128


@dataclass(frozen=True, slots=True)
class ScanInput:
    """Validated input for the scan upload pipeline."""

    image_bytes: bytes
    original_filename: str
    file_mime_type: str
    patient_mrn: str


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def validate_scan_input(
    *,
    image_bytes: bytes,
    original_filename: str,
    file_mime_type: str,
    patient_mrn: str,
) -> ScanInput:
    """Validate raw inputs. Raises on any violation."""
    if not image_bytes:
        raise BadRequest("Image file is empty")

    if len(image_bytes) < _MIN_IMAGE_BYTES:
        raise BadRequest(f"Image too small (min {_MIN_IMAGE_BYTES} bytes)")

    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise PayloadTooLarge(
            f"Image exceeds {_MAX_IMAGE_BYTES} bytes",
            context={"size": len(image_bytes), "max": _MAX_IMAGE_BYTES},
        )

    if not original_filename or len(original_filename) > 255:
        raise BadRequest("Invalid filename")

    normalized_mime = file_mime_type.split(";")[0].strip().lower()
    if normalized_mime not in _ALLOWED_MIME_TYPES:
        raise UnsupportedMediaType(
            f"Unsupported image type: {file_mime_type}",
            context={"allowed": sorted(_ALLOWED_MIME_TYPES)},
        )

    mrn = patient_mrn.strip()
    if not (_MIN_MRN_LEN <= len(mrn) <= _MAX_MRN_LEN):
        raise BadRequest(
            f"patient_mrn length must be between {_MIN_MRN_LEN} and {_MAX_MRN_LEN}",
        )
    if "\x00" in mrn:
        raise BadRequest("patient_mrn contains invalid characters")

    return ScanInput(
        image_bytes=image_bytes,
        original_filename=original_filename,
        file_mime_type=normalized_mime,
        patient_mrn=mrn,
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
async def process_scan_upload(
    *,
    clinician_id: UUID,
    clinician_email: str,
    hospital_node: str,
    image_bytes: bytes,
    original_filename: str,
    file_mime_type: str,
    patient_mrn: str,
    client_ip: str | None = None,
) -> ScanUploadResponse:
    """Run the full upload pipeline and return the response.

    Raises:
        BadRequest, PayloadTooLarge, UnsupportedMediaType: input validation.
        StorageError: on storage failure (blob will not be left behind).
        EncryptionError: on crypto failure.
        Exception: on DB failure (blob is deleted as compensating action).
    """
    # --- Step 1: Validate ---
    validated = validate_scan_input(
        image_bytes=image_bytes,
        original_filename=original_filename,
        file_mime_type=file_mime_type,
        patient_mrn=patient_mrn,
    )

    # --- Step 2: Pseudonymize MRN ---
    key_provider = KeyProvider()
    pseudonym = key_provider.pseudonym_for(
        validated.patient_mrn, hospital_node
    )

    # --- Step 3: Encrypt image ---
    master_key = key_provider.master_key
    blob: EncryptedBlob = encrypt(validated.image_bytes, master_key)
    ciphertext_sha256 = sha256_hex(blob.ciphertext)

    # --- Step 4: Prepare metadata ---
    scan_id = uuid4()
    storage_path = build_storage_path(
        hospital_node=hospital_node,
        scan_id=scan_id,
    )

    log.info(
        "scan.pipeline.begin",
        extra={
            "scan_id": str(scan_id),
            "hospital_node": hospital_node,
            "size_bytes": len(validated.image_bytes),
            "storage_path": storage_path,
        },
    )

    # --- Step 5: Upload to storage ---
    await upload_encrypted(path=storage_path, data=blob.ciphertext)

    # --- Step 6: Write scans row (with compensating delete on failure) ---
    try:
        scan_row = await insert_scan(
            scan_id=scan_id,
            clinician_id=clinician_id,
            hospital_node=hospital_node,
            patient_pseudonym=pseudonym,
            original_filename=validated.original_filename,
            file_mime_type=validated.file_mime_type,
            encrypted_file_path=storage_path,
            file_size_bytes=len(validated.image_bytes),
            sha256_hash=ciphertext_sha256,
            encryption_algorithm="AES-256-GCM",
            iv_base64=blob.iv_base64,
            tag_base64=blob.tag_base64,
        )
    except Exception as db_exc:
        log.exception(
            "scan.pipeline.db_write_failed",
            extra={"scan_id": str(scan_id), "storage_path": storage_path},
        )
        # Compensating action: delete the orphan blob
        try:
            await delete_encrypted(path=storage_path)
            log.warning(
                "scan.pipeline.compensation_succeeded",
                extra={"scan_id": str(scan_id)},
            )
        except Exception:
            log.critical(
                "scan.pipeline.compensation_failed",
                extra={
                    "scan_id": str(scan_id),
                    "storage_path": storage_path,
                    "message": "Orphan blob left in storage; manual cleanup required",
                },
            )
        # Re-raise the original DB failure
        raise db_exc

    # --- Step 7: Write audit log ---
    # If this fails, we have a scans row but no audit entry. That is
    # worse than the reverse — but the audit trigger is designed to
    # rarely fail (metadata whitelist). We let the exception propagate
    # so the caller sees the failure. The scans row remains (it's a
    # legitimate scan); a subsequent retry can add the audit entry.
    chain_seq = await append_audit_event(
        actor_id=clinician_id,
        actor_email=clinician_email,
        hospital_node=hospital_node,
        action="scan.uploaded",
        event_subtype="scan.uploaded",
        payload_sha256=ciphertext_sha256,
        scan_id=scan_id,
        client_ip=client_ip,
        extra_metadata={
            "reason": "clinician_initiated_upload",
        },
    )

    log.info(
        "scan.pipeline.complete",
        extra={
            "scan_id": str(scan_id),
            "audit_chain_seq": chain_seq,
        },
    )

    return ScanUploadResponse(
        scan_id=scan_row.id,
        status=scan_row.status,
        hospital_node=scan_row.hospital_node,
        patient_pseudonym=scan_row.patient_pseudonym,
        file_size_bytes=scan_row.file_size_bytes,
        encrypted_file_path=scan_row.encrypted_file_path,
        sha256_hash=scan_row.sha256_hash,
        audit_chain_seq=chain_seq,
        created_at=scan_row.created_at,
    )