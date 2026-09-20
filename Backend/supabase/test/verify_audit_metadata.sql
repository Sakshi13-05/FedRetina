-- ============================================================================
-- Test suite for audit_logs metadata whitelist.
-- Every block is expected to be REJECTED (constraint violation).
-- Passes when all blocks raise a check_violation (SQLSTATE 23514).
-- ============================================================================

-- Setup: ensure a scan row exists so FK is satisfiable
DO $$
DECLARE
    v_scan_id UUID;
    v_user_id UUID;
BEGIN
    SELECT id INTO v_user_id FROM auth.users LIMIT 1;
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'TEST SETUP FAILED: no auth.users row exists';
    END IF;

    INSERT INTO public.scans (
        clinician_id, hospital_node, patient_pseudonym, original_filename,
        file_mime_type, encrypted_file_path, file_size_bytes,
        sha256_hash, iv_base64, tag_base64
    )
    VALUES (
        v_user_id, 'Node 01', 'TEST-PSEUDONYM', 'test.png',
        'image/png', 'vault/test.enc', 1024,
        repeat('a', 64), 'aXY=', 'dGFn'
    )
    RETURNING id INTO v_scan_id;

    RAISE NOTICE 'Test scan seeded: %', v_scan_id;
END $$;

-- ---------------------------------------------------------------------------
-- Helper: run a CASE, expect it to fail with 23514
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION pg_temp.expect_metadata_rejected(
    p_label TEXT, p_metadata JSONB
) RETURNS TEXT
LANGUAGE plpgsql AS $$
DECLARE
    v_actor UUID;
    v_scan  UUID;
BEGIN
    SELECT id INTO v_actor FROM auth.users LIMIT 1;
    SELECT id INTO v_scan  FROM public.scans LIMIT 1;

    BEGIN
        INSERT INTO public.audit_logs (
            scan_id, actor_id, actor_email, hospital_node, action,
            payload_sha256, metadata
        ) VALUES (
            v_scan, v_actor, 'test@fedretina.local', 'Node 01', 'test.action',
            repeat('b', 64), p_metadata
        );
        -- If we get here, the constraint did NOT fire -> test failure
        RAISE EXCEPTION 'TEST FAILED [%]: constraint did not reject', p_label;
    EXCEPTION
        WHEN check_violation THEN
            RETURN format('PASS [%s]', p_label);
        WHEN raise_exception THEN
            RAISE;
    END;
END;
$$;

-- ---------------------------------------------------------------------------
-- Test cases
-- ---------------------------------------------------------------------------
SELECT pg_temp.expect_metadata_rejected(
    'unknown key',
    '{"totally_unexpected": 1}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'fl_round wrong type',
    '{"fl_round": "forty-seven"}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'fl_round out of range',
    '{"fl_round": 99999}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'dp_epsilon too large',
    '{"dp_epsilon": 999}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'predicted_grade out of range',
    '{"predicted_grade": 7}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'uncertainty_score out of range',
    '{"uncertainty_score": 1.5}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'model_version with HTML',
    '{"model_version": "<script>x</script>"}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'gradcam_path with path traversal',
    '{"gradcam_path": "../etc/passwd"}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'reason with spaces (free text / PHI risk)',
    '{"reason": "Patient John Doe, DOB 1962-03-14"}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'event_subtype unknown',
    '{"event_subtype": "made.up.event"}'::jsonb
);

SELECT pg_temp.expect_metadata_rejected(
    'error_code with lowercase',
    '{"error_code": "encryption_failed"}'::jsonb
);

-- ---------------------------------------------------------------------------
-- Positive tests: these should SUCCEED
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    v_actor UUID;
    v_scan  UUID;
BEGIN
    SELECT id INTO v_actor FROM auth.users LIMIT 1;
    SELECT id INTO v_scan  FROM public.scans LIMIT 1;

    INSERT INTO public.audit_logs (
        scan_id, actor_id, actor_email, hospital_node, action,
        payload_sha256, metadata
    ) VALUES (
        v_scan, v_actor, 'test@fedretina.local', 'Node 01', 'inference.completed',
        repeat('c', 64),
        '{
            "model_version": "fedretina-v1.3.0-r47",
            "model_hash": "' || repeat('d', 64) || '",
            "fl_round": 47,
            "dp_epsilon": 2.5,
            "dp_delta": 0.00001,
            "dp_clip_norm": 1.0,
            "dp_noise_multiplier": 1.1,
            "inference_duration_ms": 2431,
            "mc_dropout_passes": 30,
            "predicted_grade": 2,
            "uncertainty_score": 0.18,
            "confidence_score": 0.82,
            "gradcam_path": "heatmaps/scan-123.png",
            "event_subtype": "inference.completed",
            "reason": "low_confidence_manual_review"
        }'::jsonb
    );
    RAISE NOTICE 'PASS [full valid metadata accepted]';
END $$;

DROP FUNCTION pg_temp.expect_metadata_rejected(TEXT, JSONB);