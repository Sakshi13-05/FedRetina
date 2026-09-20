-- ============================================================================
-- Immutability tests for public.audit_logs
--
-- These tests are EXPECTED TO FAIL. A passing run of this file looks like
-- three error messages, each confirming the immutability trigger fired.
--
-- Run with:
--   psql "$DATABASE_URL" -f supabase/tests/verify_audit_immutability.sql
--
-- Or, if using a proper test framework (pgTAP), see the alternative below.
-- ============================================================================

-- Test 1: UPDATE should raise P0001
DO $$
BEGIN
    UPDATE public.audit_logs SET action = 'tampered' WHERE chain_seq = 1;
    RAISE EXCEPTION 'TEST FAILED: UPDATE was allowed on audit_logs';
EXCEPTION
    WHEN raise_exception THEN
        RAISE NOTICE 'TEST PASSED: UPDATE was blocked -> %', SQLERRM;
END $$;

-- Test 2: DELETE should raise P0001
DO $$
BEGIN
    DELETE FROM public.audit_logs WHERE chain_seq = 1;
    RAISE EXCEPTION 'TEST FAILED: DELETE was allowed on audit_logs';
EXCEPTION
    WHEN raise_exception THEN
        RAISE NOTICE 'TEST PASSED: DELETE was blocked -> %', SQLERRM;
END $$;

-- Test 3: TRUNCATE should raise P0001
DO $$
BEGIN
    TRUNCATE public.audit_logs;
    RAISE EXCEPTION 'TEST FAILED: TRUNCATE was allowed on audit_logs';
EXCEPTION
    WHEN raise_exception THEN
        RAISE NOTICE 'TEST PASSED: TRUNCATE was blocked -> %', SQLERRM;
END $$;