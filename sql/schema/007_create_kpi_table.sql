-- ── KPI Snapshots ────────────────────────────────────────────
-- Stores point-in-time KPI values.
-- Every time the analytics engine runs, one row per KPI is added.
-- This allows tracking KPI changes over time.

CREATE TABLE IF NOT EXISTS kpi_snapshots (
    kpi_id        SERIAL PRIMARY KEY,
    captured_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    kpi_name      VARCHAR(100) NOT NULL,
    kpi_value     NUMERIC(15,2),
    kpi_unit      VARCHAR(20),
    dimension     VARCHAR(100),
    dimension_value VARCHAR(100)
);