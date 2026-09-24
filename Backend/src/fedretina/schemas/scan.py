"""Pydantic models for the /v1/scans endpoint."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScanUploadResponse(BaseModel):
    """Response body for POST /v1/scans."""

    model_config = ConfigDict(frozen=True)

    scan_id: UUID
    status: str
    hospital_node: str
    patient_pseudonym: str
    file_size_bytes: int
    encrypted_file_path: str
    sha256_hash: str
    audit_chain_seq: int = Field(..., description="Position in the audit chain")
    created_at: datetime


class ScanDetail(BaseModel):
    """Response body for GET /v1/scans/{scan_id}."""

    model_config = ConfigDict(frozen=True)

    scan_id: UUID
    status: str
    hospital_node: str
    patient_pseudonym: str
    original_filename: str
    file_mime_type: str
    file_size_bytes: int
    sha256_hash: str
    encryption_algorithm: str
    created_at: datetime
    updated_at: datetime