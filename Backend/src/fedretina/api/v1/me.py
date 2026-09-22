"""GET /v1/me — returns the authenticated user's profile.

This endpoint exists to prove the auth chain works end-to-end. It is also
useful to the frontend for refreshing profile state without going through
Supabase directly.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from fedretina.api.deps import get_current_user
from fedretina.schemas.auth import CurrentUser

router = APIRouter(tags=["auth"])


class MeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    email: str
    full_name: str
    hospital_name: str
    hospital_node: str
    professional_role: str
    roles: list[str]

    @classmethod
    def from_user(cls, user: CurrentUser) -> MeResponse:
        return cls(
            user_id=str(user.user_id),
            email=str(user.email),
            full_name=user.full_name,
            hospital_name=user.hospital_name,
            hospital_node=user.hospital_node,
            professional_role=user.professional_role,
            roles=sorted(user.roles),
        )


@router.get("/me", response_model=MeResponse, summary="Get current user profile")
async def me(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MeResponse:
    return MeResponse.from_user(user)