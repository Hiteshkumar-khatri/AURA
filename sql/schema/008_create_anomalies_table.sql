-- ── Anomaly Detection Results ────────────────────────────────
-- Stores anomalies detected by the anomaly detection engine.
-- Each row is one detected anomaly with evidence.

CREATE TABLE IF NOT EXISTS anomaly_findings (
    anomaly_id      SERIAL PRIMARY KEY,
    detected_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    anomaly_type    VARCHAR(50)  NOT NULL,
    dimension       VARCHAR(100),
    dimension_value VARCHAR(100),
    metric_name     VARCHAR(100),
    observed_value  NUMERIC(15,2),
    expected_value  NUMERIC(15,2),
    z_score         NUMERIC(8,4),
    severity        VARCHAR(20),
    description     TEXT
);