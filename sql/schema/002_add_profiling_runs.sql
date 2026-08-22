-- ── Profiling Runs ───────────────────────────────────────────
-- One row per complete profiling session across all datasets.
-- Use this to query "latest run" without getting duplicates.

CREATE TABLE IF NOT EXISTS profiling_runs (
    run_id        SERIAL PRIMARY KEY,
    started_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMP,
    status        VARCHAR(20) NOT NULL DEFAULT 'running',
    datasets_count INTEGER,
    total_rows    BIGINT
);

-- Add run_id column to dataset_profiles
ALTER TABLE dataset_profiles 
ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES profiling_runs(run_id);