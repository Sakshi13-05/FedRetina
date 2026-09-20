-- Walks the audit chain in order and asserts each link is intact.
-- Returns 0 rows if the chain is clean.
WITH ordered AS (
    SELECT
        id,
        chain_seq,
        prev_entry_hash,
        record_hash,
        LAG(record_hash) OVER (ORDER BY chain_seq) AS expected_prev
    FROM public.audit_logs
)
SELECT
    id,
    chain_seq,
    prev_entry_hash,
    expected_prev,
    record_hash
FROM ordered
WHERE chain_seq > 1
  AND prev_entry_hash IS DISTINCT FROM expected_prev;