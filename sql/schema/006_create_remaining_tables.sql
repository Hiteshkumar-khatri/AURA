-- ── Remaining Raw Tables ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw_order_items (
    order_id             VARCHAR(50),
    order_item_id        INTEGER,
    product_id           VARCHAR(50),
    seller_id            VARCHAR(50),
    shipping_limit_date  TIMESTAMP,
    price                NUMERIC(10,2),
    freight_value        NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS raw_order_reviews (
    review_id                VARCHAR(50),
    order_id                 VARCHAR(50),
    review_score             INTEGER,
    review_comment_title     TEXT,
    review_comment_message   TEXT,
    review_creation_date     TIMESTAMP,
    review_answer_timestamp  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_products (
    product_id                   VARCHAR(50) PRIMARY KEY,
    product_category_name        VARCHAR(100),
    product_name_lenght          NUMERIC(10,2),
    product_description_lenght   NUMERIC(10,2),
    product_photos_qty           NUMERIC(10,2),
    product_weight_g             NUMERIC(10,2),
    product_length_cm            NUMERIC(10,2),
    product_height_cm            NUMERIC(10,2),
    product_width_cm             NUMERIC(10,2)
);