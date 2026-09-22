"""Cryptographic primitives for FedRetina.

This module is the entire cryptographic surface of the backend. Every
privacy guarantee the system makes — image confidentiality, tamper
detection, patient pseudonymization — is implemented here and nowhere else.

Design principles
-----------------
1. **Audited primitives only.** We use AES-256-GCM (NIST SP 800-38D) and
   HMAC-SHA256 (RFC 2104). No homemade crypto, no exotic modes.

2. **Authenticated encryption.** GCM provides both confidentiality and
   integrity. Tampering with ciphertext, IV, or tag is detected on decrypt.

3. **Random, per-encryption IVs.** Every call to ``encrypt`` generates a
   fresh 96-bit IV from ``secrets``. IV reuse under GCM is catastrophic;
   we never derive IVs from counters, timestamps, or user input.

4. **No key material in exceptions or logs.** All errors raise generic
   messages. Keys never appear in ``repr()``, stack traces, or telemetry.

5. **Explicit endianness and encoding.** All byte-to-text conversions use
   UTF-8; all base64 is standard (RFC 4648) with padding.

Threat model
------------
- The master encryption key is protected by the process environment (today)
  or a KMS (future). An attacker with filesystem read access to the running
  process CAN exfiltrate the key. This is the standard model for server-side
  encryption; it is explicitly NOT "encryption where the server is the enemy."

- An attacker with database access but NOT key access sees only ciphertext
  and is cryptographically unable to recover plaintext.

- An attacker who can modify the database but not the key cannot forge
  valid ciphertext: they would need to produce a valid GCM tag, which
  requires the key.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from fedretina.config import get_settings
from fedretina.exceptions import EncryptionError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AES_KEY_BYTES: int = 32          # AES-256
GCM_IV_BYTES: int = 12           # 96-bit nonce, the GCM-recommended size
GCM_TAG_BYTES: int = 16          # 128-bit authentication tag
SHA256_HEX_LEN: int = 64


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class EncryptedBlob:
    """The result of encrypting a byte payload with AES-256-GCM.

    All byte fields are stored internally as ``bytes``. The base64
    properties are provided because the ``scans`` table stores them in
    base64-encoded columns (``iv_base64``, ``tag_base64``).
    """

    ciphertext: bytes
    iv: bytes
    tag: bytes

    def __post_init__(self) -> None:
        if len(self.iv) != GCM_IV_BYTES:
            raise ValueError(f"IV must be {GCM_IV_BYTES} bytes, got {len(self.iv)}")
        if len(self.tag) != GCM_TAG_BYTES:
            raise ValueError(f"tag must be {GCM_TAG_BYTES} bytes, got {len(self.tag)}")
        if len(self.ciphertext) == 0:
            raise ValueError("ciphertext must not be empty")

    @property
    def iv_base64(self) -> str:
        return base64.b64encode(self.iv).decode("ascii")

    @property
    def tag_base64(self) -> str:
        return base64.b64encode(self.tag).decode("ascii")

    @property
    def ciphertext_base64(self) -> str:
        return base64.b64encode(self.ciphertext).decode("ascii")

    @classmethod
    def from_base64(
        cls,
        *,
        ciphertext_b64: str,
        iv_b64: str,
        tag_b64: str,
    ) -> EncryptedBlob:
        try:
            return cls(
                ciphertext=base64.b64decode(ciphertext_b64, validate=True),
                iv=base64.b64decode(iv_b64, validate=True),
                tag=base64.b64decode(tag_b64, validate=True),
            )
        except Exception as exc:
            raise EncryptionError(
                "EncryptedBlob: invalid base64 in one or more fields",
            ) from exc

    def __repr__(self) -> str:
        # Never include ciphertext bytes in repr — logs might capture them.
        return (
            f"EncryptedBlob(ciphertext_len={len(self.ciphertext)}, "
            f"iv_len={len(self.iv)}, tag_len={len(self.tag)})"
        )


# ---------------------------------------------------------------------------
# Core primitives
# ---------------------------------------------------------------------------
def encrypt(
    plaintext: bytes,
    key: bytes,
    *,
    associated_data: bytes | None = None,
) -> EncryptedBlob:
    """Encrypt ``plaintext`` with AES-256-GCM.

    Args:
        plaintext: The bytes to encrypt. Must not be empty.
        key: 32-byte AES-256 key.
        associated_data: Optional Additional Authenticated Data (AAD). It is
            authenticated but not encrypted. If supplied at encryption time,
            the exact same value MUST be supplied at decryption time.

    Returns:
        EncryptedBlob containing ciphertext, IV, and authentication tag.

    Raises:
        EncryptionError: if the key is the wrong length or plaintext is empty.
    """
    if len(key) != AES_KEY_BYTES:
        raise EncryptionError(f"AES key must be {AES_KEY_BYTES} bytes")
    if len(plaintext) == 0:
        raise EncryptionError("plaintext must not be empty")

    iv = secrets.token_bytes(GCM_IV_BYTES)
    aesgcm = AESGCM(key)

    try:
        # The `cryptography` library appends the 16-byte tag to the
        # ciphertext. We split it out to match our schema, which stores
        # iv and tag as separate columns.
        combined = aesgcm.encrypt(iv, plaintext, associated_data)
    except Exception as exc:
        raise EncryptionError("encryption failed") from exc

    ciphertext = combined[:-GCM_TAG_BYTES]
    tag = combined[-GCM_TAG_BYTES:]

    return EncryptedBlob(ciphertext=ciphertext, iv=iv, tag=tag)


def decrypt(
    blob: EncryptedBlob,
    key: bytes,
    *,
    associated_data: bytes | None = None,
) -> bytes:
    """Decrypt an EncryptedBlob with AES-256-GCM.

    Args:
        blob: The encrypted blob produced by :func:`encrypt`.
        key: 32-byte AES-256 key.
        associated_data: Must match the value used at encryption time,
            or decryption will fail.

    Returns:
        The original plaintext bytes.

    Raises:
        EncryptionError: if the key is wrong, the ciphertext is tampered,
            or associated_data does not match.
    """
    if len(key) != AES_KEY_BYTES:
        raise EncryptionError(f"AES key must be {AES_KEY_BYTES} bytes")

    aesgcm = AESGCM(key)
    combined = blob.ciphertext + blob.tag

    try:
        return aesgcm.decrypt(blob.iv, combined, associated_data)
    except InvalidTag as exc:
        # The most important security signal in the system: someone tried to
        # decrypt tampered data, or supplied the wrong key.
        raise EncryptionError("authentication tag verification failed") from exc
    except Exception as exc:
        raise EncryptionError("decryption failed") from exc


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of ``data``."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("sha256_hex expects bytes")
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Pseudonymization
# ---------------------------------------------------------------------------
def hmac_pseudonymize(
    mrn: str,
    node_hmac_key: bytes,
    *,
    context: str = "fedretina.pseudonym.v1",
) -> str:
    """Produce a deterministic, one-way pseudonym for a patient MRN.

    Args:
        mrn: The real Medical Record Number. Must not be empty.
        node_hmac_key: 32-byte HMAC key specific to a hospital node.
        context: A domain-separation string. Changing it changes the output
            for the same inputs, which is why it's versioned. Bump the
            version if the derivation logic ever changes.

    Returns:
        A 64-character lowercase hex string. Safe to store in the database.

    Security properties:
        * One-way: computing ``mrn`` from the pseudonym requires breaking
          HMAC-SHA256, which is infeasible.
        * Deterministic per node: the same MRN at the same node produces
          the same pseudonym, so longitudinal linkage is preserved.
        * Cross-node isolation: the same MRN at different nodes produces
          different pseudonyms, because the HMAC key differs per node.

    Domain separation note:
        The ``context`` prefix prevents the HMAC output from being confused
        with any other HMAC usage in the system. If we later add another
        keyed derivation (e.g., for searchable encryption), it must use
        a different context.
    """
    if not mrn:
        raise EncryptionError("MRN must not be empty")
    if len(node_hmac_key) != 32:
        raise EncryptionError("HMAC key must be 32 bytes")

    message = f"{context}:{mrn}".encode("utf-8")
    digest = hmac.new(node_hmac_key, message, hashlib.sha256).hexdigest()
    return digest


# ---------------------------------------------------------------------------
# Key provider
# ---------------------------------------------------------------------------
class KeyProvider:
    """Supplies cryptographic keys to the application.

    Today: reads from the process environment (via Settings).
    Tomorrow: could delegate to AWS KMS, GCP KMS, or HashiCorp Vault
    without changing any call site.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def master_key(self) -> bytes:
        """The AES-256-GCM master key used to encrypt scan images."""
        return self._settings.master_key_bytes

    def node_hmac_key(self, hospital_node: str) -> bytes:
        """Return the HMAC key for a specific hospital node."""
        return self._settings.node_hmac_key_bytes(hospital_node)

    def pseudonym_for(self, mrn: str, hospital_node: str) -> str:
        """Convenience: compute the pseudonym for an MRN at a given node."""
        return hmac_pseudonymize(mrn, self.node_hmac_key(hospital_node))


# ---------------------------------------------------------------------------
# Constant-time comparison helper
# ---------------------------------------------------------------------------
def constant_time_eq(a: bytes, b: bytes) -> bool:
    """Constant-time byte comparison. Never use ``==`` on secrets."""
    return hmac.compare_digest(a, b)