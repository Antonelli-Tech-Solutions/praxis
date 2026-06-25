-- Add outcome/trust-feedback counters to existing `facts` rows.
--
-- New fresh databases get these from the schema.sql baseline (CREATE TABLE facts);
-- this migration adds them to databases that already have the table. Retrieval
-- folds the two counts into a per-fact utility multiplier (Fact.utility) so a fact
-- whose suggested action keeps failing sinks in ranking and a proven one holds.
-- Purely additive and idempotent (IF NOT EXISTS); re-running is harmless.

ALTER TABLE facts ADD COLUMN IF NOT EXISTS success_count integer NOT NULL DEFAULT 0;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS failure_count integer NOT NULL DEFAULT 0;
