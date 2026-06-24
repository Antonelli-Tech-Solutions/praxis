-- Drop the now-dead `candidates` table.
--
-- Runs last: 0001 reads `candidates` to lift its rows onto `facts`, so the
-- drop must come after it. Idempotent via IF EXISTS.
--
-- depends: 0001_reembed_candidates 0002_retenant_orphans

DROP TABLE IF EXISTS candidates;
