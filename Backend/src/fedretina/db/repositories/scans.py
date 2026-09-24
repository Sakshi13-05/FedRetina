"""Scan repository — reads and writes the scans table."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fedretina.db.postgres import get_pool
from fedretina.logging import get_logger

log = get_logger("db.repositories.scans")


@dataclass(frozen=True, slots=True)
class ScanRow:
    """A row from public.scans."""

    id: UUID
    clinician_id: UUID | None
    hospital_node: str
    patient_pseudonym: str
    original_filename: str
    file_mime_type: str
    encrypted_file_path: str
    file_size_bytes: int
    sha256_hash: str
    encryption_algorithm: str
    iv_base64: str
    tag_base64: str
    status: str
    created_at: datetime
    updated_at: datetime


async def insert_scan(
    *,
    scan_id: UUID,
    clinician_id: UUID,
    hospital_node: str,
    patient_pseudonym: str,
    original_filename: str,
    file_mime_type: str,
    encrypted_file_path: str,
    file_size_bytes: int,
    sha256_hash: str,
    encryption_algorithm: str,
    iv_base64: str,
    tag_base64: str,
) -> ScanRow:
    """Insert a new row into public.scans and return it.

    Raises:
        asyncpg.UniqueViolationError: if scan_id already exists.
        asyncpg.Error: on any other DB error.
    """
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO public.scans (
                id, clinician_id, hospital_node, patient_pseudonym,
                original_filename, file_mime_type, encrypted_file_path,
                file_size_bytes, sha256_hash, encryption_algorithm,
                iv_base64, tag_base64, status
            )
            VALUES (
                $1, $2, $3, $4,
                $5, $6, $7,
                $8, $9, $10,
                $11, $12, 'encrypted_stored'
            )
            RETURNING *
            """,
            scan_id,
            clinician_id,
            hospital_node,
            patient_pseudonym,
            original_filename,
            file_mime_type,
            encrypted_file_path,
            file_size_bytes,
            sha256_hash,
            encryption_algorithm,
            iv_base64,
            tag_base64,
        )

    if row is None:
        raise RuntimeError("INSERT INTO scans returned no row")

    log.info(
        "scan.inserted",
        extra={"scan_id": str(scan_id), "hospital_node": hospital_node},
    )

    return ScanRow(
        id=row["id"],
        clinician_id=row["clinician_id"],
        hospital_node=row["hospital_node"],
        patient_pseudonym=row["patient_pseudonym"],
        original_filename=row["original_filename"],
        file_mime_type=row["file_mime_type"],
        encrypted_file_path=row["encrypted_file_path"],
        file_size_bytes=row["file_size_bytes"],
        sha256_hash=row["sha256_hash"],
        encryption_algorithm=row["encryption_algorithm"],
        iv_base64=row["iv_base64"],
        tag_base64=row["tag_base64"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def fetch_scan_by_id(scan_id: UUID) -> ScanRow | None:
    """Fetch a scan by ID. Returns None if not found."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM public.scans WHERE id = $1",
            scan_id,
        )

    if row is None:
        return None

    return ScanRow(
        id=row["id"],
        clinician_id=row["clinician_id"],
        hospital_node=row["hospital_node"],
        patient_pseudonym=row["patient_pseudonym"],
        original_filename=row["original_filename"],
        file_mime_type=row["file_mime_type"],
        encrypted_file_path=row["encrypted_file_path"],
        file_size_bytes=row["file_size_bytes"],
        sha256_hash=row["sha256_hash"],
        encryption_algorithm=row["encryption_algorithm"],
        iv_base64=row["iv_base64"],
        tag_base64=row["tag_base64"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )