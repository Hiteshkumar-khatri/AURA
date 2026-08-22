-- ── KPI: Revenue Summary ─────────────────────────────────────
SELECT
    COUNT(DISTINCT order_id)          AS total_orders,
    ROUND(SUM(price)::numeric, 2)     AS total_revenue,
    ROUND(AVG(price)::numeric, 2)     AS avg_order_value
FROM v_orders_complete
WHERE order_status = 'delivered';


-- ── KPI: Revenue by Month ────────────────────────────────────
SELECT
    order_month,
    COUNT(DISTINCT order_id)          AS orders,
    ROUND(SUM(price)::numeric, 2)     AS revenue
FROM v_orders_complete
WHERE order_status = 'delivered'
GROUP BY order_month
ORDER BY order_month;


-- ── KPI: Revenue by Category ─────────────────────────────────
SELECT
    COALESCE(product_category_name_english, 'uncategorized') AS category,
    COUNT(DISTINCT order_id)          AS orders,
    ROUND(SUM(price)::numeric, 2)     AS revenue
FROM v_orders_complete
WHERE order_status = 'delivered'
GROUP BY category
ORDER BY revenue DESC;


-- ── KPI: Delivery Performance by State ───────────────────────
SELECT
    customer_state,
    COUNT(DISTINCT order_id)          AS orders,
    ROUND(AVG(actual_delivery_days)::numeric, 1)  AS avg_delivery_days,
    ROUND(100.0 * SUM(
        CASE WHEN actual_delivery_days <= estimated_delivery_days
        THEN 1 ELSE 0 END
    ) / COUNT(*), 1)                  AS on_time_pct
FROM v_orders_complete
WHERE order_status = 'delivered'
  AND actual_delivery_days IS NOT NULL
GROUP BY customer_state
ORDER BY orders DESC;