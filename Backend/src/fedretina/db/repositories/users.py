"""User repository — reads profiles and roles."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fedretina.db.postgres import get_pool
from fedretina.logging import get_logger

log = get_logger("db.repositories.users")


@dataclass(frozen=True, slots=True)
class UserProfile:
    user_id: UUID
    email: str
    full_name: str
    hospital_name: str
    hospital_node: str
    professional_role: str
    roles: frozenset[str]


async def fetch_user_profile(user_id: UUID, email: str) -> UserProfile | None:
    """Fetch a user's profile and application roles.

    Returns None if the user has no profile row (e.g., trigger hasn't run yet).
    """
    pool = get_pool()

    async with pool.acquire() as conn:
        profile_row = await conn.fetchrow(
            """
            SELECT id, full_name, hospital_name, hospital_node, professional_role
            FROM public.profiles
            WHERE id = $1
            """,
            user_id,
        )
        if profile_row is None:
            log.info("user.profile.missing", extra={"user_id": str(user_id)})
            return None

        role_rows = await conn.fetch(
            """
            SELECT role::text AS role
            FROM public.user_roles
            WHERE user_id = $1
            """,
            user_id,
        )

    roles = frozenset(r["role"] for r in role_rows)

    return UserProfile(
        user_id=profile_row["id"],
        email=email,
        full_name=profile_row["full_name"],
        hospital_name=profile_row["hospital_name"],
        hospital_node=profile_row["hospital_node"],
        professional_role=profile_row["professional_role"],
        roles=roles,
    )