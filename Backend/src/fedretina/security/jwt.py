"""Supabase JWT verification.

Supabase signs JWTs with ES256 (ECDSA P-256). The public keys are exposed
at a well-known JWKS endpoint. This module:

    1. Fetches and caches the JWKS (with a 1-hour TTL, refresh on cache-miss).
    2. Verifies an incoming JWT's signature against the correct key (by kid).
    3. Validates issuer, audience, and expiration.
    4. Returns a typed VerifiedToken or raises Unauthorized.

Security properties:
    * Algorithm is pinned to ES256. Tokens with `alg` set to anything else
      (including `none`, `HS256`, `RS256`) are rejected. This prevents
      the classic "algorithm confusion" attack.
    * Key lookup is by `kid`, not by trying every key. This avoids timing
      side-channels and prevents "try all keys" denial-of-service vectors.
    * Verification failures never leak the reason — every rejection
      surfaces as the same Unauthorized exception to the caller. The
      specific reason is logged at INFO level for operators.
    * The JWKS cache is single-flight: concurrent fetches for the same
      missing key coalesce into one HTTP request.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Final
from uuid import UUID

import httpx
import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    PyJWKClientError,
)

from fedretina.config import get_settings
from fedretina.exceptions import Unauthorized
from fedretina.logging import get_logger
from fedretina.schemas.auth import SupabaseJWTClaims, VerifiedToken

log = get_logger("security.jwt")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_EXPECTED_ALGORITHMS: Final[tuple[str, ...]] = ("ES256",)
_JWKS_CACHE_TTL_SECONDS: Final[int] = 3600          # 1 hour
_JWKS_HTTP_TIMEOUT_SECONDS: Final[float] = 10.0
_JWT_LEEWAY_SECONDS: Final[int] = 30                # clock skew tolerance


# ---------------------------------------------------------------------------
# JWKS cache
# ---------------------------------------------------------------------------
@dataclass
class _CacheEntry:
    client: PyJWKClient
    fetched_at: float


@dataclass
class _JWKSCache:
    """Thread-safe, single-flight JWKS cache.

    PyJWKClient handles its own HTTP caching internally, but we want an
    outer TTL and the ability to force-refresh on unknown kid. We hold a
    single client instance and rotate it every TTL.
    """

    _entry: _CacheEntry | None = field(default=None, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _jwks_url: str = field(init=False)

    def __post_init__(self) -> None:
        settings = get_settings()
        self._jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"

    async def get_client(self, *, force_refresh: bool = False) -> PyJWKClient:
        """Return a JWKS client, refreshing if stale or forced."""
        now = time.monotonic()

        async with self._lock:
            stale = (
                self._entry is None
                or force_refresh
                or (now - self._entry.fetched_at) > _JWKS_CACHE_TTL_SECONDS
            )

            if stale:
                log.info(
                    "jwks.fetch",
                    extra={"url": self._jwks_url, "force": force_refresh},
                )
                # PyJWKClient is synchronous — run it in a thread so we don't
                # block the event loop while it does HTTP.
                client = await asyncio.to_thread(
                    PyJWKClient,
                    self._jwks_url,
                    cache_keys=True,
                    lifespan=_JWKS_CACHE_TTL_SECONDS,
                    timeout=_JWKS_HTTP_TIMEOUT_SECONDS,
                )
                self._entry = _CacheEntry(client=client, fetched_at=now)

            # Tell the type checker that self._entry is definitely populated now
            assert self._entry is not None, "Cache entry should have been populated"
            
            return self._entry.client

    async def close(self) -> None:
        """No-op — PyJWKClient does not expose a close method. Present for
        symmetry with other lifecycle-aware components."""
        self._entry = None


# Module-level singleton
_jwks_cache = _JWKSCache()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def verify_supabase_jwt(token: str) -> VerifiedToken:
    """Verify a Supabase-issued JWT and return its claims.

    Args:
        token: The raw JWT string (without the ``Bearer `` prefix).

    Returns:
        A VerifiedToken with user_id, email, timestamps, and kid.

    Raises:
        Unauthorized: for any failure — malformed token, bad signature,
            expired, wrong issuer/audience, wrong algorithm, or unknown kid.
    """
    if not token or not isinstance(token, str):
        raise Unauthorized("Missing token")

    settings = get_settings()

    try:
        unverified_header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        log.info("jwt.verify.reject", extra={"reason": "malformed_header"})
        raise Unauthorized("Invalid token") from exc

    alg = unverified_header.get("alg")
    if alg not in _EXPECTED_ALGORITHMS:
        # Pin algorithm — reject everything else, including `none` and HS256.
        log.info(
            "jwt.verify.reject",
            extra={"reason": "wrong_alg", "alg": alg},
        )
        raise Unauthorized("Invalid token")

    kid = unverified_header.get("kid")
    if not kid:
        log.info("jwt.verify.reject", extra={"reason": "missing_kid"})
        raise Unauthorized("Invalid token")

    # Fetch signing key. On PyJWKClientError (unknown kid) force-refresh once.
    signing_key = None
    for attempt in (1, 2):
        try:
            client = await _jwks_cache.get_client(force_refresh=(attempt == 2))
            signing_key = await asyncio.to_thread(
                client.get_signing_key_from_jwt, token
            )
            break
        except PyJWKClientError as exc:
            log.info(
                "jwt.verify.jwks_miss",
                extra={"reason": "unknown_kid", "kid": kid, "attempt": attempt},
            )
            if attempt == 2:
                raise Unauthorized("Invalid token") from exc

    if signing_key is None:
        raise Unauthorized("Invalid token")

    # Decode + verify. PyJWT raises specific subclasses per failure mode.
    try:
        raw_claims: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=list(_EXPECTED_ALGORITHMS),
            audience="authenticated",
            issuer=f"{settings.supabase_url}/auth/v1",
            leeway=_JWT_LEEWAY_SECONDS,
            options={
                "require": ["exp", "iat", "sub", "aud", "iss"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except ExpiredSignatureError as exc:
        log.info("jwt.verify.reject", extra={"reason": "expired"})
        raise Unauthorized("Invalid token") from exc
    except InvalidAudienceError as exc:
        log.info("jwt.verify.reject", extra={"reason": "bad_audience"})
        raise Unauthorized("Invalid token") from exc
    except InvalidIssuerError as exc:
        log.info("jwt.verify.reject", extra={"reason": "bad_issuer"})
        raise Unauthorized("Invalid token") from exc
    except InvalidSignatureError as exc:
        log.info("jwt.verify.reject", extra={"reason": "bad_signature"})
        raise Unauthorized("Invalid token") from exc
    except InvalidTokenError as exc:
        log.info("jwt.verify.reject", extra={"reason": "invalid_token"})
        raise Unauthorized("Invalid token") from exc

    # Validate the claim shape with Pydantic.
    try:
        claims = SupabaseJWTClaims.model_validate(raw_claims)
    except Exception as exc:
        log.info("jwt.verify.reject", extra={"reason": "bad_claims_shape"})
        raise Unauthorized("Invalid token") from exc

    return VerifiedToken(
        user_id=claims.sub,
        email=claims.email,
        postgres_role=claims.role,
        issued_at=datetime.fromtimestamp(claims.iat, tz=timezone.utc),
        expires_at=datetime.fromtimestamp(claims.exp, tz=timezone.utc),
        kid=kid,
    )


async def close_jwks_cache() -> None:
    """Close the module-level JWKS cache. Called from app shutdown."""
    await _jwks_cache.close()


# ---------------------------------------------------------------------------
# Debug helper — intentionally NOT used in production paths
# ---------------------------------------------------------------------------
def _extract_sub_from_unverified(token: str) -> UUID | None:
    """Return the sub claim WITHOUT verifying the signature.

    DANGEROUS — do not use for authentication. Present only for debugging
    and test fixtures.
    """
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        return UUID(claims["sub"])
    except Exception:
        return None