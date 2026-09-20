-- ============================================================================
-- Migration: Audit metadata validation (trigger-based, corrected)
-- Depends on: 20260920120000_scans_audit_logs_hardened.sql
--
-- HISTORY:
--   v1 used a CHECK constraint with `<@` (JSONB contained-by). That operator
--   requires VALUE equality, not just key presence, so any metadata with
--   non-null values was rejected. This was the wrong semantics.
--
--   v2 tried a CHECK constraint with a subquery over jsonb_object_keys.
--   PostgreSQL forbids subqueries in CHECK constraints (error 0A000).
--
--   v3 (this version) moves key-validation into a BEFORE INSERT trigger,
--   which CAN use subqueries. This is the correct design.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Drop the broken CHECK-based attempts (idempotent, safe to re-run)
-- ----------------------------------------------------------------------------
ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_metadata_keys_whitelist;
ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_metadata_full_validation;
ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_metadata_keys_check;
ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_metadata_types_check;
ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_metadata_ranges_check;
ALTER TABLE public.audit_logs
    DROP CONSTRAINT IF EXISTS audit_metadata_formats_check;

DROP FUNCTION IF EXISTS public.audit_metadata_allowed_keys() CASCADE;

-- ----------------------------------------------------------------------------
-- 2. Metadata key whitelist via BEFORE INSERT trigger
--    Rejects rows whose metadata contains any key not in the allowed set.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.validate_audit_metadata_keys()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    bad_key TEXT;
BEGIN
    SELECT k INTO bad_key
    FROM jsonb_object_keys(NEW.metadata) AS k
    WHERE k NOT IN (
        'model_version','model_hash','fl_round','architecture',
        'dp_epsilon','dp_delta','dp_clip_norm','dp_noise_multiplier',
        'inference_duration_ms','mc_dropout_passes','predicted_grade',
        'uncertainty_score','confidence_score','gradcam_path',
        'event_subtype','error_code','reason'
    )
    LIMIT 1;

    IF bad_key IS NOT NULL THEN
        RAISE EXCEPTION
            'audit_logs.metadata contains disallowed key: %', bad_key
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.validate_audit_metadata_keys()
    FROM anon, authenticated, PUBLIC;

DROP TRIGGER IF EXISTS trg_validate_audit_metadata_keys ON public.audit_logs;
CREATE TRIGGER trg_validate_audit_metadata_keys
  BEFORE INSERT ON public.audit_logs
  FOR EACH ROW EXECUTE FUNCTION public.validate_audit_metadata_keys();

-- ----------------------------------------------------------------------------
-- 3. Type CHECK constraint
-- ----------------------------------------------------------------------------
ALTER TABLE public.audit_logs
    ADD CONSTRAINT audit_metadata_types_check
    CHECK (
        (NOT metadata ? 'model_version'         OR jsonb_typeof(metadata->'model_version')         = 'string')
    AND (NOT metadata ? 'model_hash'            OR jsonb_typeof(metadata->'model_hash')            = 'string')
    AND (NOT metadata ? 'fl_round'              OR jsonb_typeof(metadata->'fl_round')              = 'number')
    AND (NOT metadata ? 'architecture'          OR jsonb_typeof(metadata->'architecture')          = 'string')
    AND (NOT metadata ? 'dp_epsilon'            OR jsonb_typeof(metadata->'dp_epsilon')            = 'number')
    AND (NOT metadata ? 'dp_delta'              OR jsonb_typeof(metadata->'dp_delta')              = 'number')
    AND (NOT metadata ? 'dp_clip_norm'          OR jsonb_typeof(metadata->'dp_clip_norm')          = 'number')
    AND (NOT metadata ? 'dp_noise_multiplier'   OR jsonb_typeof(metadata->'dp_noise_multiplier')   = 'number')
    AND (NOT metadata ? 'inference_duration_ms' OR jsonb_typeof(metadata->'inference_duration_ms') = 'number')
    AND (NOT metadata ? 'mc_dropout_passes'     OR jsonb_typeof(metadata->'mc_dropout_passes')     = 'number')
    AND (NOT metadata ? 'predicted_grade'       OR jsonb_typeof(metadata->'predicted_grade')       = 'number')
    AND (NOT metadata ? 'uncertainty_score'     OR jsonb_typeof(metadata->'uncertainty_score')     = 'number')
    AND (NOT metadata ? 'confidence_score'      OR jsonb_typeof(metadata->'confidence_score')      = 'number')
    AND (NOT metadata ? 'gradcam_path'          OR jsonb_typeof(metadata->'gradcam_path')          = 'string')
    AND (NOT metadata ? 'event_subtype'         OR jsonb_typeof(metadata->'event_subtype')         = 'string')
    AND (NOT metadata ? 'error_code'            OR jsonb_typeof(metadata->'error_code')            = 'string')
    AND (NOT metadata ? 'reason'                OR jsonb_typeof(metadata->'reason')                = 'string')
    );

-- ----------------------------------------------------------------------------
-- 4. Range CHECK constraint
-- ----------------------------------------------------------------------------
ALTER TABLE public.audit_logs
    ADD CONSTRAINT audit_metadata_ranges_check
    CHECK (
        (NOT metadata ? 'fl_round'
         OR ((metadata->>'fl_round')::numeric BETWEEN 1 AND 1000))
    AND (NOT metadata ? 'dp_epsilon'
         OR ((metadata->>'dp_epsilon')::numeric > 0 AND (metadata->>'dp_epsilon')::numeric <= 10))
    AND (NOT metadata ? 'dp_delta'
         OR ((metadata->>'dp_delta')::numeric > 0 AND (metadata->>'dp_delta')::numeric < 0.001))
    AND (NOT metadata ? 'dp_clip_norm'
         OR ((metadata->>'dp_clip_norm')::numeric > 0 AND (metadata->>'dp_clip_norm')::numeric <= 10))
    AND (NOT metadata ? 'dp_noise_multiplier'
         OR ((metadata->>'dp_noise_multiplier')::numeric > 0 AND (metadata->>'dp_noise_multiplier')::numeric <= 10))
    AND (NOT metadata ? 'inference_duration_ms'
         OR ((metadata->>'inference_duration_ms')::numeric BETWEEN 0 AND 600000))
    AND (NOT metadata ? 'mc_dropout_passes'
         OR ((metadata->>'mc_dropout_passes')::numeric BETWEEN 1 AND 200))
    AND (NOT metadata ? 'predicted_grade'
         OR ((metadata->>'predicted_grade')::numeric BETWEEN 0 AND 4))
    AND (NOT metadata ? 'uncertainty_score'
         OR ((metadata->>'uncertainty_score')::numeric BETWEEN 0 AND 1))
    AND (NOT metadata ? 'confidence_score'
         OR ((metadata->>'confidence_score')::numeric BETWEEN 0 AND 1))
    );

-- ----------------------------------------------------------------------------
-- 5. Format CHECK constraint (regex + event_subtype enum + reason PHI guard)
-- ----------------------------------------------------------------------------
ALTER TABLE public.audit_logs
    ADD CONSTRAINT audit_metadata_formats_check
    CHECK (
        (NOT metadata ? 'model_version'
         OR (metadata->>'model_version') ~ '^[a-zA-Z0-9._-]{1,64}$')
    AND (NOT metadata ? 'model_hash'
         OR (metadata->>'model_hash') ~ '^[0-9a-f]{64}$')
    AND (NOT metadata ? 'error_code'
         OR (metadata->>'error_code') ~ '^[A-Z0-9_]{2,32}$')
    AND (NOT metadata ? 'gradcam_path'
         OR (
             (metadata->>'gradcam_path') ~ '^[a-zA-Z0-9._/-]{1,256}$'
             AND position('..' in (metadata->>'gradcam_path')) = 0
             AND left((metadata->>'gradcam_path'), 1) <> '/'
         ))
    AND (NOT metadata ? 'event_subtype'
         OR (metadata->>'event_subtype') IN (
             'scan.uploaded','scan.encrypted','scan.decryption_failed','scan.deleted',
             'inference.started','inference.completed','inference.failed','inference.timed_out',
             'review.flagged','review.unflagged','review.confirmed','review.overridden',
             'model.round_started','model.round_completed','model.round_failed','model.promoted','model.rolled_back',
             'anchor.created','anchor.verified','anchor.verification_failed',
             'auth.login','auth.logout','auth.failed_login','auth.password_changed',
             'admin.user_created','admin.user_deactivated','admin.role_granted','admin.role_revoked'
         ))
    AND (NOT metadata ? 'reason'
         OR (metadata->>'reason') ~ '^[a-z][a-z0-9_]{0,127}$')
    );

-- ----------------------------------------------------------------------------
-- 6. chain_anchors.metadata whitelist
-- ----------------------------------------------------------------------------
ALTER TABLE public.chain_anchors
    DROP CONSTRAINT IF EXISTS chain_anchor_metadata_whitelist;

ALTER TABLE public.chain_anchors
    ADD CONSTRAINT chain_anchor_metadata_whitelist
    CHECK (
        metadata = '{}'::jsonb
        OR (
            metadata <@ '{
                "nodes_included": null,
                "total_events": null,
                "verification_run_id": null,
                "previous_anchor_hash": null
            }'::jsonb

            AND (NOT metadata ? 'nodes_included'
                 OR (jsonb_typeof(metadata->'nodes_included') = 'array'
                     AND jsonb_array_length(metadata->'nodes_included') <= 50))
            AND (NOT metadata ? 'total_events'
                 OR (jsonb_typeof(metadata->'total_events') = 'number'
                     AND (metadata->>'total_events')::numeric >= 0))
            AND (NOT metadata ? 'verification_run_id'
                 OR (jsonb_typeof(metadata->'verification_run_id') = 'string'
                     AND (metadata->>'verification_run_id') ~ '^[a-zA-Z0-9._-]{1,64}$'))
            AND (NOT metadata ? 'previous_anchor_hash'
                 OR (jsonb_typeof(metadata->'previous_anchor_hash') = 'string'
                     AND (metadata->>'previous_anchor_hash') ~ '^[0-9a-f]{64}$'))
        )
    );

-- ----------------------------------------------------------------------------
-- 7. RLS: split insert policy by actor scope
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Clinicians append audit events in their node" ON public.audit_logs;
DROP POLICY IF EXISTS "Admins append audit events for any node" ON public.audit_logs;
DROP POLICY IF EXISTS "Clinicians append client-scoped audit events" ON public.audit_logs;
DROP POLICY IF EXISTS "Admins append admin-scoped audit events" ON public.audit_logs;

CREATE POLICY "Clinicians append client-scoped audit events"
  ON public.audit_logs FOR INSERT TO authenticated
  WITH CHECK (
      actor_id = auth.uid()
      AND hospital_node = public.current_user_hospital_node()
      AND public.current_user_hospital_node() <> 'NONE'
      AND metadata->>'event_subtype' IN (
          'scan.uploaded','scan.encrypted','scan.decryption_failed','scan.deleted',
          'auth.login','auth.logout','auth.failed_login','auth.password_changed',
          'review.flagged','review.unflagged','review.confirmed','review.overridden'
      )
      AND NOT (metadata ?| ARRAY[
          'model_version','model_hash','fl_round','architecture',
          'dp_epsilon','dp_delta','dp_clip_norm','dp_noise_multiplier',
          'predicted_grade','uncertainty_score','confidence_score',
          'mc_dropout_passes','gradcam_path'
      ])
  );

CREATE POLICY "Admins append admin-scoped audit events"
  ON public.audit_logs FOR INSERT TO authenticated
  WITH CHECK (
      public.has_role(auth.uid(), 'admin')
      AND NOT (metadata ?| ARRAY[
          'model_version','model_hash','fl_round','architecture',
          'dp_epsilon','dp_delta','dp_clip_norm','dp_noise_multiplier',
          'predicted_grade','uncertainty_score','confidence_score',
          'mc_dropout_passes','gradcam_path'
      ])
  );