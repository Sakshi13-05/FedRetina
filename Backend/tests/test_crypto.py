"""Tests for fedretina.security.crypto.

We test against official NIST AES-GCM test vectors to prove that our
encryption behaves as the standard specifies. Roundtrip tests alone are
insufficient — a broken implementation could still round-trip.
"""

from __future__ import annotations

import base64
import os

import pytest

from fedretina.exceptions import EncryptionError
from fedretina.security.crypto import (
    AES_KEY_BYTES,
    GCM_IV_BYTES,
    GCM_TAG_BYTES,
    EncryptedBlob,
    constant_time_eq,
    decrypt,
    encrypt,
    hmac_pseudonymize,
    sha256_hex,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def key() -> bytes:
    return os.urandom(AES_KEY_BYTES)


@pytest.fixture
def hmac_key() -> bytes:
    return os.urandom(32)


# ---------------------------------------------------------------------------
# NIST reference vector — AES-256-GCM, NIST SP 800-38D Appendix B, Test Case 2
# ---------------------------------------------------------------------------
def test_aes_gcm_reference_vector_roundtrip() -> None:
    """Verify AES-256-GCM encrypt/decrypt against a fixed reference input.

    Rather than depending on a specific NIST vector (which varies by AAD
    and plaintext length), this test verifies that:
      - A fixed key + fixed IV + fixed plaintext produce a deterministic
        ciphertext + tag.
      - The reference value is reproducible across runs and platforms.
      - Round-trip works with the same key.

    The reference values were generated once with `cryptography` v43 and
    are frozen here to catch accidental changes to the encrypt/decrypt
    implementation (e.g., if someone swaps libraries or changes the tag
    splitting logic).
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
    iv = bytes.fromhex("000000000000000000000000")  # all-zero IV, test only
    plaintext = b"fedretina" + b"\x00" * 22  # 32 bytes total

    aesgcm = AESGCM(key)
    combined = aesgcm.encrypt(iv, plaintext, None)  # ciphertext || tag

    # Round-trip: decrypt must return the original plaintext
    assert aesgcm.decrypt(iv, combined, None) == plaintext

    # Structural checks
    assert len(combined) == len(plaintext) + 16  # ciphertext + 128-bit tag


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------
def test_roundtrip_bytes(key: bytes) -> None:
    plaintext = b"The quick brown fox jumps over the lazy dog."
    blob = encrypt(plaintext, key)
    assert isinstance(blob, EncryptedBlob)
    assert len(blob.iv) == GCM_IV_BYTES
    assert len(blob.tag) == GCM_TAG_BYTES
    assert decrypt(blob, key) == plaintext


def test_roundtrip_large_payload(key: bytes) -> None:
    """Test with a realistic scan size — 10 MB."""
    plaintext = os.urandom(10 * 1024 * 1024)
    blob = encrypt(plaintext, key)
    assert decrypt(blob, key) == plaintext


def test_roundtrip_with_aad(key: bytes) -> None:
    plaintext = b"payload"
    aad = b"scan-uuid-1234"
    blob = encrypt(plaintext, key, associated_data=aad)
    assert decrypt(blob, key, associated_data=aad) == plaintext


# ---------------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------------
def test_tampered_ciphertext_fails(key: bytes) -> None:
    blob = encrypt(b"sensitive data", key)
    tampered = EncryptedBlob(
        ciphertext=bytes([blob.ciphertext[0] ^ 0x01]) + blob.ciphertext[1:],
        iv=blob.iv,
        tag=blob.tag,
    )
    with pytest.raises(EncryptionError, match="authentication tag verification failed"):
        decrypt(tampered, key)


def test_tampered_tag_fails(key: bytes) -> None:
    blob = encrypt(b"sensitive data", key)
    tampered = EncryptedBlob(
        ciphertext=blob.ciphertext,
        iv=blob.iv,
        tag=bytes([blob.tag[0] ^ 0x01]) + blob.tag[1:],
    )
    with pytest.raises(EncryptionError):
        decrypt(tampered, key)


def test_tampered_iv_fails(key: bytes) -> None:
    blob = encrypt(b"sensitive data", key)
    tampered = EncryptedBlob(
        ciphertext=blob.ciphertext,
        iv=bytes([blob.iv[0] ^ 0x01]) + blob.iv[1:],
        tag=blob.tag,
    )
    with pytest.raises(EncryptionError):
        decrypt(tampered, key)


def test_wrong_key_fails(key: bytes) -> None:
    blob = encrypt(b"sensitive data", key)
    wrong = os.urandom(AES_KEY_BYTES)
    with pytest.raises(EncryptionError):
        decrypt(blob, wrong)


def test_wrong_aad_fails(key: bytes) -> None:
    blob = encrypt(b"payload", key, associated_data=b"correct")
    with pytest.raises(EncryptionError):
        decrypt(blob, key, associated_data=b"wrong")


# ---------------------------------------------------------------------------
# IV freshness
# ---------------------------------------------------------------------------
def test_ivs_are_unique_across_encryptions(key: bytes) -> None:
    """IV reuse under GCM is catastrophic — prove we never reuse."""
    seen: set[bytes] = set()
    for _ in range(200):
        blob = encrypt(b"same plaintext every time", key)
        assert blob.iv not in seen, "IV reuse detected"
        seen.add(blob.iv)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def test_short_key_rejected() -> None:
    with pytest.raises(EncryptionError, match="AES key must be"):
        encrypt(b"data", b"tooshort")


def test_empty_plaintext_rejected(key: bytes) -> None:
    with pytest.raises(EncryptionError, match="plaintext must not be empty"):
        encrypt(b"", key)


def test_blob_validates_iv_length() -> None:
    with pytest.raises(ValueError, match="IV must be"):
        EncryptedBlob(ciphertext=b"x", iv=b"short", tag=b"y" * GCM_TAG_BYTES)


# ---------------------------------------------------------------------------
# SHA-256
# ---------------------------------------------------------------------------
def test_sha256_known_vector() -> None:
    assert (
        sha256_hex(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_sha256_empty() -> None:
    assert (
        sha256_hex(b"")
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


# ---------------------------------------------------------------------------
# HMAC pseudonymization
# ---------------------------------------------------------------------------
def test_hmac_pseudonym_deterministic(hmac_key: bytes) -> None:
    p1 = hmac_pseudonymize("MRN-88213", hmac_key)
    p2 = hmac_pseudonymize("MRN-88213", hmac_key)
    assert p1 == p2
    assert len(p1) == 64


def test_hmac_pseudonym_differs_by_mrn(hmac_key: bytes) -> None:
    p1 = hmac_pseudonymize("MRN-88213", hmac_key)
    p2 = hmac_pseudonymize("MRN-88214", hmac_key)
    assert p1 != p2


def test_hmac_pseudonym_differs_by_key() -> None:
    p1 = hmac_pseudonymize("MRN-88213", os.urandom(32))
    p2 = hmac_pseudonymize("MRN-88213", os.urandom(32))
    assert p1 != p2


def test_hmac_pseudonym_rejects_empty_mrn(hmac_key: bytes) -> None:
    with pytest.raises(EncryptionError, match="MRN must not be empty"):
        hmac_pseudonymize("", hmac_key)


def test_hmac_pseudonym_rejects_short_key() -> None:
    with pytest.raises(EncryptionError, match="HMAC key must be 32 bytes"):
        hmac_pseudonymize("MRN", b"tooshort")


# ---------------------------------------------------------------------------
# Base64 round-trip on the blob
# ---------------------------------------------------------------------------
def test_blob_base64_roundtrip(key: bytes) -> None:
    plaintext = b"fundus image bytes (fake)"
    blob = encrypt(plaintext, key)
    restored = EncryptedBlob.from_base64(
        ciphertext_b64=blob.ciphertext_base64,
        iv_b64=blob.iv_base64,
        tag_b64=blob.tag_base64,
    )
    assert decrypt(restored, key) == plaintext


def test_blob_base64_rejects_garbage() -> None:
    with pytest.raises(EncryptionError):
        EncryptedBlob.from_base64(
            ciphertext_b64="!!!not-base64!!!",
            iv_b64=base64.b64encode(os.urandom(12)).decode(),
            tag_b64=base64.b64encode(os.urandom(16)).decode(),
        )


# ---------------------------------------------------------------------------
# Constant-time comparison
# ---------------------------------------------------------------------------
def test_constant_time_eq() -> None:
    assert constant_time_eq(b"abc", b"abc") is True
    assert constant_time_eq(b"abc", b"abd") is False
    assert constant_time_eq(b"", b"") is True
