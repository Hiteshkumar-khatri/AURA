-- ── AURA Metadata Schema ─────────────────────────────────────
-- This file creates the tables AURA uses to track its own work.
-- Run this once to initialize the database.

-- ── Pipeline Jobs ────────────────────────────────────────────
-- Every time AURA processes a dataset, one row is recorded here.
CREATE TABLE IF NOT EXISTS pipeline_jobs (
    job_id        SERIAL PRIMARY KEY,
    started_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMP,
    status        VARCHAR(20) NOT NULL DEFAULT 'running',
    dataset_name  VARCHAR(255),
    rows_input    INTEGER,
    rows_output   INTEGER,
    error_message TEXT
);

-- ── Dataset Profiles ─────────────────────────────────────────
-- Stores the output of the profiler for every dataset processed.
CREATE TABLE IF NOT EXISTS dataset_profiles (
    profile_id    SERIAL PRIMARY KEY,
    job_id        INTEGER REFERENCES pipeline_jobs(job_id),
    profiled_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    dataset_name  VARCHAR(255) NOT NULL,
    row_count     INTEGER,
    column_count  INTEGER,
    duplicate_rows INTEGER,
    quality_score NUMERIC(5,2)
);

-- ── Column Profiles ──────────────────────────────────────────
-- Stores per-column statistics for every dataset profiled.
CREATE TABLE IF NOT EXISTS column_profiles (
    column_profile_id  SERIAL PRIMARY KEY,
    profile_id         INTEGER REFERENCES dataset_profiles(profile_id),
    column_name        VARCHAR(255) NOT NULL,
    data_type          VARCHAR(50),
    missing_count      INTEGER,
    missing_pct        NUMERIC(5,2),
    unique_count       INTEGER
);