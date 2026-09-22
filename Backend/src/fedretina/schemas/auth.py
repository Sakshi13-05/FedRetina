"""Authentication data models.

These Pydantic v2 models describe:

    VerifiedToken — what we extract from a valid Supabase JWT
    CurrentUser   — the fully-resolved user context used by endpoints

Both are frozen (immutable) so nothing downstream can mutate the
authenticated principal.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------------------------------------------------------------------------
# JWT claims — what Supabase puts in the token
# ---------------------------------------------------------------------------
class SupabaseJWTClaims(BaseModel):
    """The subset of Supabase JWT claims we rely on.

    Supabase issues tokens with these claims (in addition to standard JWT
    claims like ``iat``, ``exp``, ``nbf``):

        sub   — the auth.users.id of the authenticated user (UUID)
        email — the user's email
        role  — the *Postgres* role (``authenticated``, ``anon``, or
                ``service_role``), not the *application* role. Application
                roles live in ``public.user_roles``.
        aud   — audience, usually ``authenticated``
        iss   — issuer, the Supabase project URL
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    sub: UUID
    email: EmailStr
    role: Literal["authenticated", "anon", "service_role"]
    aud: str
    iss: str
    exp: int
    iat: int
    nbf: int | None = None


# ---------------------------------------------------------------------------
# Verified token — the result of successful verification
# ---------------------------------------------------------------------------
class VerifiedToken(BaseModel):
    """A Supabase JWT that passed all verification checks."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID = Field(..., description="auth.users.id from the `sub` claim")
    email: EmailStr
    postgres_role: Literal["authenticated", "anon", "service_role"]
    issued_at: datetime
    expires_at: datetime
    kid: str = Field(..., description="Key ID used to verify the signature")


# ---------------------------------------------------------------------------
# Current user — the fully-resolved request principal
# ---------------------------------------------------------------------------
class CurrentUser(BaseModel):
    """The authenticated user, enriched with profile and roles.

    This is what FastAPI dependencies inject into endpoint handlers. It
    carries everything an endpoint needs to make an authorization decision
    without further database lookups.
    """

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    email: EmailStr
    full_name: str
    hospital_name: str
    hospital_node: str
    professional_role: str
    roles: frozenset[str] = Field(
        default_factory=frozenset,
        description="Application roles from public.user_roles (admin, clinician, ...)",
    )

    def has_role(self, *role_names: str) -> bool:
        """Return True if the user has any of the given roles."""
        return any(r in self.roles for r in role_names)

    def is_admin(self) -> bool:
        return "admin" in self.roles