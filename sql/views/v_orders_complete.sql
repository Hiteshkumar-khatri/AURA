-- ── Complete Orders View ─────────────────────────────────────
-- Joins orders, items, products, customers and payments
-- into one queryable view for analytics.
-- This is the primary view for KPI calculations.

CREATE OR REPLACE VIEW v_orders_complete AS
SELECT
    -- Order identifiers
    o.order_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,

    -- Customer
    o.customer_id,
    c.customer_city,
    c.customer_state,

    -- Item details
    i.order_item_id,
    i.product_id,
    i.seller_id,
    i.price,
    i.freight_value,
    i.price + i.freight_value AS total_item_value,

    -- Product
    p.product_category_name,
    ct.product_category_name_english,

    -- Derived date fields
    DATE_TRUNC('month', o.order_purchase_timestamp) AS order_month,
    EXTRACT(YEAR  FROM o.order_purchase_timestamp)  AS order_year,
    EXTRACT(MONTH FROM o.order_purchase_timestamp)  AS order_month_num,

    -- Delivery metrics
    EXTRACT(EPOCH FROM (
        o.order_delivered_customer_date - o.order_purchase_timestamp
    )) / 86400 AS actual_delivery_days,

    EXTRACT(EPOCH FROM (
        o.order_estimated_delivery_date - o.order_purchase_timestamp
    )) / 86400 AS estimated_delivery_days

FROM raw_orders o
LEFT JOIN raw_customers      c  ON o.customer_id   = c.customer_id
LEFT JOIN raw_order_items    i  ON o.order_id      = i.order_id
LEFT JOIN raw_products       p  ON i.product_id    = p.product_id
LEFT JOIN raw_category_translation ct 
                                ON p.product_category_name = ct.product_category_name;