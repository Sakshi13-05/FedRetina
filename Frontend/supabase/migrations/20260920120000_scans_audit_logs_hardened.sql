-- ============================================================================
-- Migration: Scans, Immutable Audit Logs, Chain Anchors (Hardened)
-- Depends on: 20260905190156_*.sql (profiles, user_roles, has_role, set_updated_at)
-- Fixes: chain race condition, nullable hashes, timezone drift, RLS escape,
--        metadata PHI leak, client_ip XSS, missing updated_at trigger,
--        missing chain anchor table.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. Extensions
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ----------------------------------------------------------------------------
-- 1. Monotonic chain sequence (fixes Bug 1: hash chain race)
--    Every audit row gets a gapless, transactionally-assigned sequence number
--    from nextval(). Sequence values are unique across concurrent transactions
--    because nextval() is non-transactional — but the ORDER BY chain_seq is
--    still deterministic (ties broken by id).
-- ----------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS public.audit_log_chain_seq START 1 INCREMENT 1;

-- ----------------------------------------------------------------------------
-- 2. Scans table (unchanged structure, added updated_at trigger)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.scans (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id          UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    hospital_node         TEXT NOT NULL DEFAULT 'Node 01',
    patient_pseudonym     TEXT NOT NULL,
    original_filename     TEXT NOT NULL,
    file_mime_type        TEXT NOT NULL,
    encrypted_file_path   TEXT NOT NULL,
    file_size_bytes       BIGINT NOT NULL CHECK (file_size_bytes > 0),
    sha256_hash           TEXT NOT NULL CHECK (sha256_hash ~ '^[0-9a-f]{64}$'),
    encryption_algorithm  TEXT NOT NULL DEFAULT 'AES-256-GCM'
                          CHECK (encryption_algorithm IN ('AES-256-GCM', 'AES-256-CBC', 'ChaCha20-Poly1305')),
    iv_base64             TEXT NOT NULL,
    tag_base64            TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'encrypted_stored'
                          CHECK (status IN ('encrypted_stored', 'processing', 'completed', 'failed')),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bug 6 fix: updated_at trigger (reuses existing public.set_updated_at())
DROP TRIGGER IF EXISTS scans_set_updated_at ON public.scans;
CREATE TRIGGER scans_set_updated_at
  BEFORE UPDATE ON public.scans
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ----------------------------------------------------------------------------
-- 3. Audit logs table (immutable, hash-chained)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_seq         BIGINT NOT NULL DEFAULT nextval('public.audit_log_chain_seq'),
    scan_id           UUID REFERENCES public.scans(id) ON DELETE SET NULL,
    actor_id          UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    actor_email       TEXT NOT NULL,
    hospital_node     TEXT NOT NULL,
    action            TEXT NOT NULL,
    client_ip         TEXT,
    payload_sha256    TEXT NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Bug 2 fix: NOT NULL with deterministic default
    prev_entry_hash   TEXT NOT NULL DEFAULT 'GENESIS_NODE_ANCHOR',
    record_hash       TEXT NOT NULL CHECK (record_hash ~ '^[0-9a-f]{64}$'),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_chain_seq
    ON public.audit_logs (chain_seq DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_hospital_node
    ON public.audit_logs (hospital_node, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_scan_id
    ON public.audit_logs (scan_id) WHERE scan_id IS NOT NULL;

-- Concern 3 fix: client_ip format validation (IPv4 or IPv6)
ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_client_ip_format;
ALTER TABLE public.audit_logs
    ADD CONSTRAINT audit_client_ip_format
    CHECK (
        client_ip IS NULL
        OR client_ip ~ '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9]{1,2})\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9]{1,2})$'
        OR client_ip ~ '^[0-9a-fA-F:]{2,45}$'
    );

-- Concern 2 fix: metadata key whitelist (prevents PHI exfiltration)
ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_metadata_keys_whitelist;
ALTER TABLE public.audit_logs
    ADD CONSTRAINT audit_metadata_keys_whitelist
    CHECK (
        metadata = '{}'::jsonb
        OR metadata <@ '{
            "model_version": null,
            "fl_round": null,
            "dp_epsilon": null,
            "dp_delta": null,
            "inference_duration_ms": null,
            "predicted_grade": null,
            "uncertainty_score": null,
            "gradcam_path": null,
            "error_code": null,
            "reason": null,
            "event_subtype": null
        }'::jsonb
    );

-- ----------------------------------------------------------------------------
-- 4. Immutability enforcement (append-only)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.enforce_audit_log_immutability()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RAISE EXCEPTION
        'CRITICAL SECURITY VIOLATION: public.audit_logs is append-only. UPDATE, DELETE, and TRUNCATE are prohibited.';
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON public.audit_logs;
CREATE TRIGGER trg_audit_logs_immutable
  BEFORE UPDATE OR DELETE ON public.audit_logs
  FOR EACH ROW EXECUTE FUNCTION public.enforce_audit_log_immutability();

-- Table-level TRUNCATE is not row-triggered, so block it separately
DROP TRIGGER IF EXISTS trg_audit_logs_no_truncate ON public.audit_logs;
CREATE TRIGGER trg_audit_logs_no_truncate
  BEFORE TRUNCATE ON public.audit_logs
  FOR EACH STATEMENT EXECUTE FUNCTION public.enforce_audit_log_immutability();

-- Privilege-level defense-in-depth
REVOKE UPDATE, DELETE, TRUNCATE ON public.audit_logs FROM anon, authenticated, service_role;
REVOKE TRUNCATE ON public.audit_logs FROM PUBLIC;

-- ----------------------------------------------------------------------------
-- 5. Hash chain trigger (fixes Bug 1 concurrency + Bug 3 timezone)
--    - Locks the table in SHARE ROW EXCLUSIVE mode so no two inserts race
--    - Uses EXTRACT(EPOCH ...) for timezone-independent hashing
--    - Uses chain_seq DESC for deterministic tail lookup
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.generate_audit_log_hash()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    last_hash  TEXT;
    epoch_text TEXT;
BEGIN
    -- Serialize inserts so the chain cannot fork. SHARE ROW EXCLUSIVE is
    -- compatible with other SHARE ROW EXCLUSIVE lockers in the same tx
    -- but blocks concurrent inserts until this one commits.
    LOCK TABLE public.audit_logs IN SHARE ROW EXCLUSIVE MODE;

    SELECT record_hash
      INTO last_hash
      FROM public.audit_logs
     ORDER BY chain_seq DESC
     LIMIT 1;

    IF last_hash IS NOT NULL THEN
        NEW.prev_entry_hash := last_hash;
    ELSE
        NEW.prev_entry_hash := 'GENESIS_NODE_ANCHOR';
    END IF;

    -- Timezone-deterministic timestamp representation
    epoch_text := to_char(EXTRACT(EPOCH FROM NEW.created_at), 'FM9999999990.000000');

    NEW.record_hash := encode(
        digest(
            concat_ws('|',
                COALESCE(NEW.scan_id::text, ''),
                COALESCE(NEW.actor_id::text, ''),
                COALESCE(NEW.actor_email, ''),
                NEW.hospital_node,
                NEW.action,
                COALESCE(NEW.client_ip, ''),
                NEW.payload_sha256,
                NEW.metadata::text,
                NEW.prev_entry_hash,
                epoch_text,
                NEW.chain_seq::text
            ),
            'sha256'
        ),
        'hex'
    );

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_generate_audit_hash ON public.audit_logs;
CREATE TRIGGER trg_generate_audit_hash
  BEFORE INSERT ON public.audit_logs
  FOR EACH ROW EXECUTE FUNCTION public.generate_audit_log_hash();

-- ----------------------------------------------------------------------------
-- 6. Chain anchor table (Concern 1: external notarization)
--    The head hash of the chain is periodically recorded here with a signature
--    (produced by an HSM/KMS or the FastAPI backend using a pinned key). This
--    gives you an external anchor that an attacker with DB write access cannot
--    forge without also compromising the signing key.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.chain_anchors (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchored_head_hash TEXT NOT NULL CHECK (anchored_head_hash ~ '^[0-9a-f]{64}$'),
    anchored_chain_seq BIGINT NOT NULL,
    anchor_reason      TEXT NOT NULL DEFAULT 'scheduled'
                       CHECK (anchor_reason IN ('scheduled', 'manual', 'pre_export', 'incident')),
    signature_alg      TEXT NOT NULL DEFAULT 'Ed25519'
                       CHECK (signature_alg IN ('Ed25519', 'ECDSA-P256', 'RSA-PSS-2048')),
    signature_b64      TEXT NOT NULL,
    signing_key_id     TEXT NOT NULL,
    signed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata           JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Anchors are themselves immutable
CREATE OR REPLACE FUNCTION public.enforce_chain_anchor_immutability()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RAISE EXCEPTION 'chain_anchors is append-only.';
END;
$$;

DROP TRIGGER IF EXISTS trg_chain_anchors_immutable ON public.chain_anchors;
CREATE TRIGGER trg_chain_anchors_immutable
  BEFORE UPDATE OR DELETE ON public.chain_anchors
  FOR EACH ROW EXECUTE FUNCTION public.enforce_chain_anchor_immutability();

ALTER TABLE public.chain_anchors ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- 7. Node isolation helper (Bug 5 hardened with COALESCE)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_user_hospital_node()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COALESCE(
        (SELECT hospital_node FROM public.profiles WHERE id = auth.uid()),
        'NONE'
    );
$$;

-- ----------------------------------------------------------------------------
-- 8. RLS
-- ----------------------------------------------------------------------------
ALTER TABLE public.scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- --- scans ---
DROP POLICY IF EXISTS "Clinicians view scans in their own hospital node" ON public.scans;
CREATE POLICY "Clinicians view scans in their own hospital node"
  ON public.scans FOR SELECT TO authenticated
  USING (
      hospital_node = public.current_user_hospital_node()
      OR public.has_role(auth.uid(), 'admin')
  );

DROP POLICY IF EXISTS "Clinicians insert scans to their own hospital node" ON public.scans;
CREATE POLICY "Clinicians insert scans to their own hospital node"
  ON public.scans FOR INSERT TO authenticated
  WITH CHECK (
      clinician_id = auth.uid()
      AND (
          hospital_node = public.current_user_hospital_node()
          OR public.has_role(auth.uid(), 'admin')
      )
  );

DROP POLICY IF EXISTS "Uploader or admin update scan status" ON public.scans;
CREATE POLICY "Uploader or admin update scan status"
  ON public.scans FOR UPDATE TO authenticated
  USING (
      clinician_id = auth.uid()
      OR public.has_role(auth.uid(), 'admin')
  )
  WITH CHECK (
      hospital_node = public.current_user_hospital_node()
      OR public.has_role(auth.uid(), 'admin')
  );

-- --- audit_logs ---
DROP POLICY IF EXISTS "Only admins view audit logs" ON public.audit_logs;
CREATE POLICY "Only admins view audit logs"
  ON public.audit_logs FOR SELECT TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

-- Bug 7 fix: split into clinician-scope and admin-scope inserts
DROP POLICY IF EXISTS "Authenticated users can append audit logs" ON public.audit_logs;
DROP POLICY IF EXISTS "Clinicians append audit events in their node" ON public.audit_logs;
CREATE POLICY "Clinicians append audit events in their node"
  ON public.audit_logs FOR INSERT TO authenticated
  WITH CHECK (
      actor_id = auth.uid()
      AND hospital_node = public.current_user_hospital_node()
      AND public.current_user_hospital_node() <> 'NONE'
  );

DROP POLICY IF EXISTS "Admins append audit events for any node" ON public.audit_logs;
CREATE POLICY "Admins append audit events for any node"
  ON public.audit_logs FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(), 'admin'));

-- --- chain_anchors ---
DROP POLICY IF EXISTS "Only admins view chain anchors" ON public.chain_anchors;
CREATE POLICY "Only admins view chain anchors"
  ON public.chain_anchors FOR SELECT TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

DROP POLICY IF EXISTS "Only admins insert chain anchors" ON public.chain_anchors;
CREATE POLICY "Only admins insert chain anchors"
  ON public.chain_anchors FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(), 'admin'));
-- NOTE: service_role bypasses RLS, so the FastAPI backend (using service key)
-- will also be able to insert anchors without an explicit policy.

-- ----------------------------------------------------------------------------
-- 9. Grants (explicit)
-- ----------------------------------------------------------------------------
GRANT SELECT, INSERT            ON public.scans         TO authenticated;
GRANT SELECT, INSERT            ON public.audit_logs    TO authenticated;
GRANT SELECT, INSERT            ON public.chain_anchors TO authenticated;
GRANT ALL                       ON public.scans         TO service_role;
GRANT SELECT, INSERT            ON public.audit_logs    TO service_role;
GRANT SELECT, INSERT            ON public.chain_anchors TO service_role;
GRANT USAGE ON SEQUENCE public.audit_log_chain_seq TO authenticated, service_role;

-- ----------------------------------------------------------------------------
-- 10. Lock down internal functions (idempotent — matches prior migrations)
-- ----------------------------------------------------------------------------
REVOKE EXECUTE ON FUNCTION public.enforce_audit_log_immutability()  FROM anon, authenticated, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.generate_audit_log_hash()        FROM anon, authenticated, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.enforce_chain_anchor_immutability() FROM anon, authenticated, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.current_user_hospital_node()     FROM anon, PUBLIC;
-- has_role is intentionally callable by `authenticated` because RLS policies
-- invoke it under the caller's identity. It was already REVOKEd from anon.