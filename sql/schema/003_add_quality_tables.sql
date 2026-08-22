-- ── Data Quality Findings ────────────────────────────────────
-- One row per problem detected in a dataset.

CREATE TABLE IF NOT EXISTS quality_findings (
    finding_id    SERIAL PRIMARY KEY,
    profile_id    INTEGER REFERENCES dataset_profiles(profile_id),
    run_id        INTEGER REFERENCES profiling_runs(run_id),
    dataset_name  VARCHAR(255) NOT NULL,
    column_name   VARCHAR(255),
    finding_type  VARCHAR(50)  NOT NULL,
    severity      VARCHAR(20)  NOT NULL,
    description   TEXT,
    affected_rows INTEGER,
    affected_pct  NUMERIC(5,2),
    detected_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ── Quality Scores ───────────────────────────────────────────
-- One row per dataset per run. The final quality judgment.

CREATE TABLE IF NOT EXISTS quality_scores (
    score_id      SERIAL PRIMARY KEY,
    profile_id    INTEGER REFERENCES dataset_profiles(profile_id),
    run_id        INTEGER REFERENCES profiling_runs(run_id),
    dataset_name  VARCHAR(255) NOT NULL,
    score         NUMERIC(5,2) NOT NULL,
    total_findings     INTEGER DEFAULT 0,
    critical_findings  INTEGER DEFAULT 0,
    high_findings      INTEGER DEFAULT 0,
    medium_findings    INTEGER DEFAULT 0,
    low_findings       INTEGER DEFAULT 0,
    scored_at     TIMESTAMP NOT NULL DEFAULT NOW()
);