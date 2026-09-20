-- ============================================================================
-- Preflight: detect existing audit_logs rows that would violate the new
-- metadata whitelist / event_subtype enum / reason PHI guard.
-- Must return ZERO rows before applying the migration.
-- ============================================================================
WITH violations AS (
    SELECT
        id,
        chain_seq,
        action,
        metadata,
        -- 1. Unknown keys
        (SELECT array_agg(k)
         FROM jsonb_object_keys(metadata) AS k
         WHERE k NOT IN (
            'model_version','model_hash','fl_round','architecture',
            'dp_epsilon','dp_delta','dp_clip_norm','dp_noise_multiplier',
            'inference_duration_ms','mc_dropout_passes','predicted_grade',
            'uncertainty_score','confidence_score','gradcam_path',
            'event_subtype','error_code','reason'
         )) AS unknown_keys,
        -- 2. Wrong types
        (metadata ? 'fl_round' AND jsonb_typeof(metadata -> 'fl_round') <> 'number') AS fl_round_type_bad,
        (metadata ? 'dp_epsilon' AND jsonb_typeof(metadata -> 'dp_epsilon') <> 'number') AS dp_eps_type_bad,
        (metadata ? 'predicted_grade' AND jsonb_typeof(metadata -> 'predicted_grade') <> 'number') AS grade_type_bad,
        (metadata ? 'reason' AND jsonb_typeof(metadata -> 'reason') <> 'string') AS reason_type_bad,
        -- 3. Out-of-range values
        (metadata ? 'fl_round' AND (metadata ->> 'fl_round')::numeric < 1) AS fl_round_range_bad,
        (metadata ? 'fl_round' AND (metadata ->> 'fl_round')::numeric > 1000) AS fl_round_range_bad2,
        (metadata ? 'dp_epsilon' AND (metadata ->> 'dp_epsilon')::numeric <= 0) AS dp_eps_range_bad,
        (metadata ? 'predicted_grade' AND (metadata ->> 'predicted_grade')::numeric NOT BETWEEN 0 AND 4) AS grade_range_bad,
        (metadata ? 'uncertainty_score' AND (metadata ->> 'uncertainty_score')::numeric NOT BETWEEN 0 AND 1) AS unc_range_bad,
        -- 4. Bad reason format (PHI / free text)
        (metadata ? 'reason' AND (metadata ->> 'reason') !~ '^[a-z][a-z0-9_]{0,127}$') AS reason_format_bad,
        -- 5. Unknown event_subtype
        (metadata ? 'event_subtype' AND (metadata ->> 'event_subtype') NOT IN (
            'scan.uploaded','scan.encrypted','scan.decryption_failed','scan.deleted',
            'inference.started','inference.completed','inference.failed','inference.timed_out',
            'review.flagged','review.unflagged','review.confirmed','review.overridden',
            'model.round_started','model.round_completed','model.round_failed','model.promoted','model.rolled_back',
            'anchor.created','anchor.verified','anchor.verification_failed',
            'auth.login','auth.logout','auth.failed_login','auth.password_changed',
            'admin.user_created','admin.user_deactivated','admin.role_granted','admin.role_revoked'
        )) AS subtype_bad
    FROM public.audit_logs
)
SELECT * FROM violations
WHERE
    unknown_keys IS NOT NULL
    OR fl_round_type_bad OR dp_eps_type_bad OR grade_type_bad OR reason_type_bad
    OR fl_round_range_bad OR fl_round_range_bad2
    OR dp_eps_range_bad OR grade_range_bad OR unc_range_bad
    OR reason_format_bad OR subtype_bad;