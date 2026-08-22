-- ── Raw Data Tables ──────────────────────────────────────────
-- These tables store the Olist data exactly as-is from CSV.
-- No cleaning applied at this stage.
-- Prefix: raw_ to distinguish from future cleaned tables.

CREATE TABLE IF NOT EXISTS raw_customers (
    customer_id              VARCHAR(50) PRIMARY KEY,
    customer_unique_id       VARCHAR(50),
    customer_zip_code_prefix VARCHAR(10),
    customer_city            VARCHAR(100),
    customer_state           VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS raw_sellers (
    seller_id                VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix   VARCHAR(10),
    seller_city              VARCHAR(100),
    seller_state             VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS raw_order_payments (
    order_id             VARCHAR(50),
    payment_sequential   INTEGER,
    payment_type         VARCHAR(50),
    payment_installments INTEGER,
    payment_value        NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS raw_category_translation (
    product_category_name         VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);