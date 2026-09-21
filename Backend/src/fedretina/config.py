"""Application configuration.

All environment variables are read, validated, and typed through this module.
If any required value is missing or malformed, ``Settings()`` raises at import
time — the process fails fast and loud, never silently.
"""

from __future__ import annotations

import base64
import binascii
import re
from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_AES_KEY_BYTES = 32
_HMAC_KEY_BYTES = 32
_MIN_JWT_SECRET_BYTES = 32
_ALLOWED_NODES = {"Node 01", "Node 02", "Node 03"}


class Settings(BaseSettings):
    """Fully validated application settings.

    Instances are created once via :func:`get_settings` and cached.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------
    env: Literal["development", "staging", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_reload: bool = False

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    supabase_url: str = Field(..., min_length=1)
    supabase_anon_key: SecretStr
    supabase_service_role_key: SecretStr
    supabase_jwt_secret: SecretStr = Field(..., validation_alias="SUPABASE_JWT_SECRET")

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: SecretStr

    # ------------------------------------------------------------------
    # Encryption keys (base64-encoded, 32 raw bytes each)
    # ------------------------------------------------------------------
    fedretina_master_key_b64: SecretStr
    fedretina_node_hmac_key_node01_b64: SecretStr
    fedretina_node_hmac_key_node02_b64: SecretStr
    fedretina_node_hmac_key_node03_b64: SecretStr

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    supabase_scans_bucket: str = Field(default="fedretina-scans", min_length=1)

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ------------------------------------------------------------------
    # Server hardening
    # ------------------------------------------------------------------
    request_timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_upload_size_bytes: int = Field(default=26_214_400, ge=1_048_576)

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("supabase_url")
    @classmethod
    def _validate_supabase_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with https://")
        return v.rstrip("/")

    @field_validator("supabase_jwt_secret")
    @classmethod
    def _validate_jwt_secret_strength(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        if len(raw.encode("utf-8")) < _MIN_JWT_SECRET_BYTES:
            raise ValueError(
                f"SUPABASE_JWT_SECRET must be at least {_MIN_JWT_SECRET_BYTES} bytes",
            )
        return v

    @field_validator("database_url")
    @classmethod
    def _validate_db_url(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        if not raw.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a postgresql:// URI")
        # Reject unencoded @ inside the password segment — a common footgun.
        # The URI format is: scheme://user:password@host:port/db
        scheme_end = raw.index("://") + 3
        authority_end = raw.find("/", scheme_end)
        authority = raw[scheme_end:authority_end]
        if authority.count("@") > 1:
            raise ValueError(
                "DATABASE_URL contains an unencoded '@' in the password. "
                "URL-encode it (e.g. '@' -> '%40') or use the Session Pooler URI.",
            )
        return v

    @field_validator(
        "fedretina_master_key_b64",
        "fedretina_node_hmac_key_node01_b64",
        "fedretina_node_hmac_key_node02_b64",
        "fedretina_node_hmac_key_node03_b64",
    )
    @classmethod
    def _validate_base64_32byte_key(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("key must be valid base64") from exc
        if len(decoded) != _AES_KEY_BYTES:
            raise ValueError(
                f"key must decode to exactly {_AES_KEY_BYTES} bytes "
                f"(got {len(decoded)})",
            )
        return v

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a clean list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def master_key_bytes(self) -> bytes:
        """Raw 32-byte master encryption key."""
        return base64.b64decode(self.fedretina_master_key_b64.get_secret_value())

    def node_hmac_key_bytes(self, hospital_node: str) -> bytes:
        """Raw 32-byte HMAC key for a specific hospital node.

        Raises:
            ValueError: if ``hospital_node`` is not one of the known nodes.
        """
        if hospital_node not in _ALLOWED_NODES:
            raise ValueError(f"unknown hospital node: {hospital_node!r}")
        attr = {
            "Node 01": "fedretina_node_hmac_key_node01_b64",
            "Node 02": "fedretina_node_hmac_key_node02_b64",
            "Node 03": "fedretina_node_hmac_key_node03_b64",
        }[hospital_node]
        secret: SecretStr = getattr(self, attr)
        return base64.b64decode(secret.get_secret_value())

    # ------------------------------------------------------------------
    # Safety guard: never run in production with CORS wildcard
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _forbid_wildcard_cors_in_prod(self) -> Settings:
        if self.is_production and "*" in self.cors_origin_list:
            raise ValueError("CORS '*' is forbidden in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance.

    Call this from anywhere. The first call reads ``.env`` and validates;
    subsequent calls return the cached instance.
    """
    return Settings()  # type: ignore[call-arg]


def _urlencode_password(uri: str) -> str:
    """Utility to URL-encode an unencoded password in a postgres URI.

    Only used in tests and migration helper scripts.
    """
    m = re.match(
        r"^(?P<scheme>postgres(?:ql)?://)(?P<user>[^:@/]+):(?P<pwd>[^@]*)@(?P<rest>.+)$",
        uri,
    )
    if not m:
        return uri
    return f"{m['scheme']}{m['user']}:{quote_plus(m['pwd'])}@{m['rest']}"