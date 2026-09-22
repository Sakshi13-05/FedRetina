"""Aggregate router for API v1.

Mounts all v1 sub-routers. New modules add themselves here.
"""

from __future__ import annotations

from fastapi import APIRouter

from fedretina.api.v1 import me

api_v1_router = APIRouter()
api_v1_router.include_router(me.router)