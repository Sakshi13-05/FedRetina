"""FastAPI dependency providers.

Provides:
    get_current_user    — full authentication: verifies JWT, loads profile+roles
    require_role        — factory for role-gated endpoints

The dependencies deliberately write request-scoped context to contextvars
so our JSON logger picks them up automatically.
"""
from __future__ import annotations
from collections.abc import Callable,Awaitable
from typing import Annotated
from fastapi import Depends, Header
from fedretina.api.context import bind_request_context
from fedretina.db.repositories.users import fetch_user_profile
from fedretina.exceptions import Forbidden, Unauthorized
from fedretina.logging import get_logger
from fedretina.schemas.auth import CurrentUser
from fedretina.security.jwt import verify_supabase_jwt

log = get_logger("api.deps")


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> CurrentUser:
    """Verify the Bearer JWT, load the user's profile and roles.

    Raises:
        Unauthorized: if the header is missing/malformed or the token is invalid.
        Forbidden:    if the user has a valid token but no profile row yet.
    """
    if not authorization:
        raise Unauthorized("Missing Authorization header")

    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise Unauthorized("Authorization header must be 'Bearer <token>'")

    token = parts[1].strip()
    if not token:
        raise Unauthorized("Empty bearer token")

    verified = await verify_supabase_jwt(token)

    profile = await fetch_user_profile(verified.user_id, str(verified.email))
    if profile is None:
        # Valid token, but no profile row. This happens if handle_new_user
        # hasn't run, or the user was deleted from profiles.
        log.info(
            "auth.profile_missing",
            extra={"user_id": str(verified.user_id)},
        )
        raise Forbidden("User profile not found")

    user = CurrentUser(
        user_id=profile.user_id,
        email=profile.email,
        full_name=profile.full_name,
        hospital_name=profile.hospital_name,
        hospital_node=profile.hospital_node,
        professional_role=profile.professional_role,
        roles=profile.roles,
    )

    # Bind context so downstream log records carry actor identity
    bind_request_context(
        actor_id=str(user.user_id),
        actor_email=user.email,
        hospital_node=user.hospital_node,
    )

    return user


def require_role(
    *role_names: str,
) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Return a dependency that allows only the specified roles.

    Usage::

        @router.get("/admin-only")
        async def admin_only(
            user: CurrentUser = Depends(require_role("admin")),
        ) -> ...:
            ...
    """
    if not role_names:
        raise ValueError("require_role requires at least one role name")

    allowed = frozenset(role_names)

    async def _check(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if not user.roles & allowed:
            log.info(
                "auth.role_denied",
                extra={
                    "user_id": str(user.user_id),
                    "user_roles": sorted(user.roles),
                    "required_roles": sorted(allowed),
                },
            )
            raise Forbidden("Insufficient permissions")
        return user

    return _check