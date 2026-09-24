"""This code defines the strictly structured data formats (Pydantic models) your application uses to handle file operations with Supabase Storage,this code prevents bugs before they happen. """

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UploadResult(BaseModel):
    """Returned after a successful upload to Supabase Storage."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(..., description="Full object path within the bucket")
    bucket: str = Field(..., description="Bucket name")
    size_bytes: int = Field(..., ge=0, description="Size of the stored object")
    sha256_hex: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 of the stored bytes, computed client-side",
    )
    uploaded_at: datetime = Field(..., description="UTC timestamp of upload")


class DownloadResult(BaseModel):
    """Returned after a successful download from Supabase Storage."""

    model_config = ConfigDict(frozen=True)

    path: str
    data: bytes
    size_bytes: int = Field(..., ge=0)


class SignedUrl(BaseModel):
    """A time-limited URL granting read access to a single object."""

    model_config = ConfigDict(frozen=True)

    url: str
    path: str
    expires_at: datetime