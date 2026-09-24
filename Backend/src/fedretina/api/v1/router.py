"""Aggregate router for API v1."""

from __future__ import annotations

from fastapi import APIRouter

from fedretina.api.v1 import me, scans

api_v1_router = APIRouter()
api_v1_router.include_router(me.router)
api_v1_router.include_router(scans.router)