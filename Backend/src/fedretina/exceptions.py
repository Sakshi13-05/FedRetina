"""Domain exception hierarchy.

Each exception maps to:
    - A stable ``code`` string (for clients to switch on)
    - An HTTP status code
    - A safe message (never leaks internals)

The global error handler (middleware/error_handler.py) converts these into
RFC 7807 Problem Details JSON responses.
"""

from __future__ import annotations

from typing import Any


class FedRetinaError(Exception):
    """Base class for all application exceptions."""

    code: str = "internal_error"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.context: dict[str, Any] = context or {}


# ---------------------------------------------------------------------------
# 4xx — client errors
# ---------------------------------------------------------------------------
class ClientError(FedRetinaError):
    """Any 4xx."""

    status_code = 400


class BadRequest(ClientError):
    code = "bad_request"
    message = "The request is malformed."


class ValidationError(ClientError):
    code = "validation_error"
    status_code = 422
    message = "One or more fields failed validation."


class Unauthorized(ClientError):
    code = "unauthorized"
    status_code = 401
    message = "Authentication required."


class Forbidden(ClientError):
    code = "forbidden"
    status_code = 403
    message = "You do not have permission to perform this action."


class NotFound(ClientError):
    code = "not_found"
    status_code = 404
    message = "The requested resource was not found."


class Conflict(ClientError):
    code = "conflict"
    status_code = 409
    message = "The request conflicts with the current state."


class PayloadTooLarge(ClientError):
    code = "payload_too_large"
    status_code = 413
    message = "The uploaded file is too large."


class UnsupportedMediaType(ClientError):
    code = "unsupported_media_type"
    status_code = 415
    message = "The uploaded file type is not supported."


class RateLimited(ClientError):
    code = "rate_limited"
    status_code = 429
    message = "Too many requests. Try again later."


# ---------------------------------------------------------------------------
# 5xx — server errors
# ---------------------------------------------------------------------------
class ServerError(FedRetinaError):
    """Any 5xx."""

    status_code = 500


class DatabaseError(ServerError):
    code = "database_error"
    message = "A database error occurred."


class StorageError(ServerError):
    code = "storage_error"
    message = "A storage error occurred."


class EncryptionError(ServerError):
    code = "encryption_error"
    message = "An encryption error occurred."


class ExternalServiceError(ServerError):
    code = "external_service_error"
    status_code = 502
    message = "An upstream service is unavailable."


class TimeoutError_(ServerError):  # noqa: N801 — avoid clashing with builtin
    code = "timeout"
    status_code = 504
    message = "The operation timed out."