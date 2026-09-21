"""Global exception handlers — convert exceptions to RFC 7807 Problem Details.

Two categories:
    1. FedRetinaError subclasses — mapped via their .status_code / .code
    2. Everything else — mapped to 500 with a generic message
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from fedretina.exceptions import FedRetinaError
from fedretina.logging import get_logger
from fedretina.middleware.request_id import get_request_id

log = get_logger("error")


def _problem(
    *,
    status: int,
    code: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build an RFC 7807 Problem Details response."""
    body: dict[str, Any] = {
        "type": f"https://docs.fedretina.local/errors/{code}",
        "title": code,
        "status": status,
        "detail": message,
    }
    if context:
        body["context"] = context
    rid = get_request_id()
    if rid:
        body["request_id"] = rid
    return JSONResponse(status_code=status, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers to the app."""

    @app.exception_handler(FedRetinaError)
    async def _domain_error(request: Request, exc: FedRetinaError) -> JSONResponse:
        log.warning(
            "domain_error",
            extra={"code": exc.code, "path": request.url.path},
        )
        return _problem(
            status=exc.status_code,
            code=exc.code,
            message=exc.message,
            context=exc.context,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        log.info("validation_error", extra={"path": request.url.path})
        return _problem(
            status=422,
            code="validation_error",
            message="One or more fields failed validation.",
            context={"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        log.info(
            "http_error",
            extra={"path": request.url.path, "status": exc.status_code},
        )
        return _problem(
            status=exc.status_code,
            code="http_error",
            message=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", extra={"path": request.url.path})
        return _problem(
            status=500,
            code="internal_error",
            message="An unexpected error occurred.",
        )