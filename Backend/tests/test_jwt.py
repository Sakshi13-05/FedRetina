"""Tests for JWT verification.

We generate an ES256 keypair locally, sign tokens, and verify that the
production verifier accepts valid tokens and rejects every category of
malformed/forged/expired token.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from fedretina.exceptions import Unauthorized
from fedretina.security.jwt import verify_supabase_jwt

# ---------------------------------------------------------------------------
# Test key setup
# ---------------------------------------------------------------------------
_TEST_KID = "test-kid-001"


def _make_es256_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(scope="module")
def private_key() -> ec.EllipticCurvePrivateKey:
    return _make_es256_key()


@pytest.fixture
def issuer() -> str:
    from fedretina.config import get_settings

    return f"{get_settings().supabase_url}/auth/v1"


def _sign(
    private_key: ec.EllipticCurvePrivateKey,
    *,
    issuer: str,
    sub: str | None = None,
    aud: str = "authenticated",
    iat: int | None = None,
    exp: int | None = None,
    kid: str = _TEST_KID,
    algorithm: str = "ES256",
    extra_claims: dict | None = None,
) -> str:
    now = int(time.time())
    claims = {
        "sub": sub or str(uuid4()),
        "email": "clinician@example.com",
        "role": "authenticated",
        "aud": aud,
        "iss": issuer,
        "iat": iat if iat is not None else now,
        "exp": exp if exp is not None else now + 3600,
        **(extra_claims or {}),
    }
    return jwt.encode(
        claims,
        private_key,
        algorithm=algorithm,
        headers={"kid": kid},
    )


# ---------------------------------------------------------------------------
# Patch the JWKS lookup — we don't want to hit Supabase in tests
# ---------------------------------------------------------------------------
class _FakeSigningKey:
    def __init__(self, key) -> None:
        self.key = key


class _FakeJWKClient:
    def __init__(self, pubkey) -> None:
        self._pub = pubkey

    def get_signing_key_from_jwt(self, _token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._pub)


@pytest.fixture
def patch_jwks(private_key: ec.EllipticCurvePrivateKey):
    """Replace the JWKS cache with one that returns our test public key."""
    public_key = private_key.public_key()
    fake_client = _FakeJWKClient(public_key)

    async def fake_get_client(*, force_refresh: bool = False):
        return fake_client

    with patch(
        "fedretina.security.jwt._jwks_cache.get_client",
        new=fake_get_client,
    ):
        yield


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_valid_token_accepted(private_key, issuer, patch_jwks) -> None:
    token = _sign(private_key, issuer=issuer)
    verified = await verify_supabase_jwt(token)
    assert verified.email == "clinician@example.com"
    assert verified.postgres_role == "authenticated"
    assert verified.kid == _TEST_KID


# ---------------------------------------------------------------------------
# Rejections
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_expired_token_rejected(private_key, issuer, patch_jwks) -> None:
    now = int(time.time())
    token = _sign(private_key, issuer=issuer, iat=now - 7200, exp=now - 3600)
    with pytest.raises(Unauthorized):
        await verify_supabase_jwt(token)


@pytest.mark.asyncio
async def test_wrong_issuer_rejected(private_key, patch_jwks) -> None:
    token = _sign(private_key, issuer="https://evil.example.com/auth/v1")
    with pytest.raises(Unauthorized):
        await verify_supabase_jwt(token)


@pytest.mark.asyncio
async def test_wrong_audience_rejected(private_key, issuer, patch_jwks) -> None:
    token = _sign(private_key, issuer=issuer, aud="something-else")
    with pytest.raises(Unauthorized):
        await verify_supabase_jwt(token)


@pytest.mark.asyncio
async def test_wrong_signature_rejected(issuer, patch_jwks) -> None:
    other_key = _make_es256_key()
    token = _sign(other_key, issuer=issuer)
    with pytest.raises(Unauthorized):
        await verify_supabase_jwt(token)


@pytest.mark.asyncio
async def test_alg_none_rejected(issuer, patch_jwks) -> None:
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "email": "x@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "iss": issuer,
            "iat": now,
            "exp": now + 3600,
        },
        key=None,
        algorithm="none",
        headers={"kid": _TEST_KID},
    )
    with pytest.raises(Unauthorized):
        await verify_supabase_jwt(token)


@pytest.mark.asyncio
async def test_malformed_token_rejected(patch_jwks) -> None:
    with pytest.raises(Unauthorized):
        await verify_supabase_jwt("not.a.jwt")
    with pytest.raises(Unauthorized):
        await verify_supabase_jwt("")
    with pytest.raises(Unauthorized):
        await verify_supabase_jwt("a.b")  # type: ignore[arg-type]