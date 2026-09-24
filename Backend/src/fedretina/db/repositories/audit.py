"""Audit log repository — append-only writes to audit_logs.

The audit_logs table enforces a metadata whitelist via triggers and
constraints. This repository guarantees that what we send matches the
allowed keys and formats, so failures surface here rather than as
opaque 23514 constraint violations at the database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fedretina.db.postgres import get_pool
from fedretina.logging import get_logger

log = get_logger("db.repositories.audit")


_ALLOWED_METADATA_KEYS = frozenset({
    "model_version", "model_hash", "fl_round", "architecture",
    "dp_epsilon", "dp_delta", "dp_clip_norm", "dp_noise_multiplier",
    "inference_duration_ms", "mc_dropout_passes", "predicted_grade",
    "uncertainty_score", "confidence_score", "gradcam_path",
    "event_subtype", "error_code", "reason",
})


async def append_audit_event(
    *,
    actor_id: UUID | None,
    actor_email: str,
    hospital_node: str,
    action: str,
    event_subtype: str,
    payload_sha256: str,
    scan_id: UUID | None = None,
    client_ip: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> int:
    """Append a single row to public.audit_logs. Returns the chain_seq.

    The database triggers fill in prev_entry_hash and record_hash
    automatically — this function only provides the content.

    Raises:
        ValueError: if metadata contains a disallowed key.
        asyncpg.Error: on any DB error.
    """
    metadata: dict[str, Any] = {"event_subtype": event_subtype}
    if extra_metadata:
        for k, v in extra_metadata.items():
            if k not in _ALLOWED_METADATA_KEYS:
                raise ValueError(f"disallowed metadata key: {k!r}")
            if k == "event_subtype":
                continue  # already set
            metadata[k] = v

    pool = get_pool()

    async with pool.acquire() as conn:
        chain_seq: int = await conn.fetchval(
            """
            INSERT INTO public.audit_logs (
                scan_id, actor_id, actor_email, hospital_node,
                action, client_ip, payload_sha256, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            RETURNING chain_seq
            """,
            scan_id,
            actor_id,
            actor_email,
            hospital_node,
            action,
            client_ip,
            payload_sha256,
            metadata,
        )

    log.info(
        "audit.appended",
        extra={
            "chain_seq": chain_seq,
            "action": action,
            "event_subtype": event_subtype,
            "scan_id": str(scan_id) if scan_id else None,
        },
    )

    return chain_seq


async def fetch_chain_head() -> tuple[int, str] | None:
    """Return (chain_seq, record_hash) of the latest entry, or None if empty."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT chain_seq, record_hash
            FROM public.audit_logs
            ORDER BY chain_seq DESC
            LIMIT 1
            """
        )
    if row is None:
        return None
    return row["chain_seq"], row["record_hash"]


async def verify_chain() -> list[tuple[int, bool]]:
    """Walk the chain and verify each link. Returns [(chain_seq, is_valid)]."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH ordered AS (
                SELECT chain_seq, prev_entry_hash, record_hash,
                       LAG(record_hash) OVER (ORDER BY chain_seq) AS expected_prev
                FROM public.audit_logs
            )
            SELECT chain_seq,
                   CASE
                       WHEN chain_seq = (SELECT MIN(chain_seq) FROM public.audit_logs)
                           THEN prev_entry_hash = 'GENESIS_NODE_ANCHOR'
                       ELSE prev_entry_hash = expected_prev
                   END AS link_ok
            FROM ordered
            ORDER BY chain_seq
            """
        )

    return [(r["chain_seq"], bool(r["link_ok"])) for r in rows]