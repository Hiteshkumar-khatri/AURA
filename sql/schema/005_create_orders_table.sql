-- ── Raw Orders Table ─────────────────────────────────────────
-- Date columns explicitly cast to TIMESTAMP during ingestion.
-- This fixes the "date as text" finding from the quality engine.

CREATE TABLE IF NOT EXISTS raw_orders (
    order_id                      VARCHAR(50) PRIMARY KEY,
    customer_id                   VARCHAR(50),
    order_status                  VARCHAR(50),
    order_purchase_timestamp      TIMESTAMP,
    order_approved_at             TIMESTAMP,
    order_delivered_carrier_date  TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);