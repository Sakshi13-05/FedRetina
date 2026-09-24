"""POST /v1/scans — upload a fundus image for screening."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from fedretina.api.deps import get_current_user
from fedretina.exceptions import NotFound
from fedretina.schemas.auth import CurrentUser
from fedretina.schemas.scan import ScanDetail, ScanUploadResponse
from fedretina.services.scan_service import process_scan_upload
from fedretina.db.repositories.scans import fetch_scan_by_id

router = APIRouter(prefix="/scans", tags=["scans"])


def _client_ip(request: Request) -> str | None:
    """Extract the client IP, honoring X-Forwarded-For if present."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post(
    "",
    response_model=ScanUploadResponse,
    status_code=201,
    summary="Upload a fundus image for DR screening",
)
async def upload_scan(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    file: Annotated[UploadFile, File(description="Fundus image file")],
    patient_mrn: Annotated[str, Form(description="Patient medical record number")],
) -> ScanUploadResponse:
    """Accept an image upload, encrypt it, store it, and audit the action."""
    image_bytes = await file.read()

    return await process_scan_upload(
        clinician_id=user.user_id,
        clinician_email=str(user.email),
        hospital_node=user.hospital_node,
        image_bytes=image_bytes,
        original_filename=file.filename or "unnamed",
        file_mime_type=file.content_type or "application/octet-stream",
        patient_mrn=patient_mrn,
        client_ip=_client_ip(request),
    )


@router.get(
    "/{scan_id}",
    response_model=ScanDetail,
    summary="Fetch metadata for a scan",
)
async def get_scan(
    scan_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ScanDetail:
    """Return scan metadata. RLS ensures cross-node isolation."""
    row = await fetch_scan_by_id(scan_id)
    if row is None:
        raise NotFound("Scan not found")
    if row.hospital_node != user.hospital_node and not user.is_admin():
        raise NotFound("Scan not found")  # do not leak existence

    return ScanDetail(
        scan_id=row.id,
        status=row.status,
        hospital_node=row.hospital_node,
        patient_pseudonym=row.patient_pseudonym,
        original_filename=row.original_filename,
        file_mime_type=row.file_mime_type,
        file_size_bytes=row.file_size_bytes,
        sha256_hash=row.sha256_hash,
        encryption_algorithm=row.encryption_algorithm,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )