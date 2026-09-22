"""FastAPI application factory.

This module builds the ASGI app that Uvicorn serves. It wires together:
    - Configuration (from config.py)
    - Structured logging (from logging.py)
    - Request-ID middleware
    - Global exception handling (RFC 7807 Problem Details)
    - CORS
    - Versioned API router (mounted at /v1)

Run with:
    uvicorn fedretina.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from fedretina.api.v1.router import api_v1_router
from fedretina.security.jwt import close_jwks_cache

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi import HTTPException
from fedretina.db.postgres import ping

from fedretina import __version__
from fedretina.config import get_settings
from fedretina.logging import configure_logging, get_logger
from fedretina.middleware.error_handler import register_exception_handlers
from fedretina.middleware.request_id import RequestIDMiddleware
from fedretina.db.postgres import close_pool, init_pool

# ---------------------------------------------------------------------------
# Logging is configured before anything else emits a line
# ---------------------------------------------------------------------------
configure_logging()
log = get_logger("main")


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: run startup and shutdown hooks."""
    settings = get_settings()

    log.info(
        "startup.begin",
        extra={
            "env": settings.env,
            "api_host": settings.api_host,
            "api_port": settings.api_port,
        },
    )

    await init_pool()
    log.info("startup.db_pool_ready")

    try:
        yield
    finally:
        await close_jwks_cache()
        log.info("shutdown.jwks_cache_closed")
        await close_pool()
        log.info("shutdown.db_pool_closed")
        log.info("shutdown.complete")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="FedRetina API",
        description="Privacy-Preserving Federated Diabetic Retinopathy Grading System",
        version=__version__,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # ------------------------------------------------------------------
    # Middleware — order matters. Request ID must be outermost so it wraps
    # everything, including CORS preflight and error responses.
    # ------------------------------------------------------------------
    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ------------------------------------------------------------------
    # Exception handlers — convert domain errors into Problem Details
    # ------------------------------------------------------------------
    register_exception_handlers(app)

    app.include_router(api_v1_router, prefix="/v1")
    
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "fedretina-backend"}

    @app.get("/ready", tags=["health"])
    async def ready() -> dict[str, str]:
        

        db_ok = await ping()
        if not db_ok:
            raise HTTPException(
                status_code=503,
                detail={"status": "unavailable", "database": "down"},
            )
        return {"status": "ok", "database": "ok"}

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "service": "fedretina-backend",
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
        }

    return app


# ---------------------------------------------------------------------------
# ASGI entry point
# ---------------------------------------------------------------------------
app = create_app()