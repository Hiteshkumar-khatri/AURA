import psycopg2
from datetime import datetime

# ── Configuration ────────────────────────────────────────────
DB_HOST = "localhost"
DB_PORT = 5433
DB_NAME = "aura"
DB_USER = "aura_user"
DB_PASS = "aura_pass"

# ── Connect ──────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASS
    )

# ── Save a KPI value ─────────────────────────────────────────
def save_kpi(cursor, conn, kpi_name, kpi_value, kpi_unit,
             dimension=None, dimension_value=None):
    cursor.execute("""
        INSERT INTO kpi_snapshots
            (kpi_name, kpi_value, kpi_unit, dimension, dimension_value)
        VALUES (%s, %s, %s, %s, %s);
    """, (kpi_name, kpi_value, kpi_unit, dimension, dimension_value))
    conn.commit()

# ── KPI 1: Revenue summary ───────────────────────────────────
def kpi_revenue_summary(cursor, conn):
    print("\n── Revenue Summary ─────────────────────────────────")

    cursor.execute("""
        SELECT
            COUNT(DISTINCT order_id)      AS total_orders,
            ROUND(SUM(price)::numeric, 2) AS total_revenue,
            ROUND(AVG(price)::numeric, 2) AS avg_order_value
        FROM v_orders_complete
        WHERE order_status = 'delivered';
    """)
    row = cursor.fetchone()
    total_orders, total_revenue, avg_order_value = row

    print(f"   Total orders:      {total_orders:,}")
    print(f"   Total revenue:     ${total_revenue:,.2f}")
    print(f"   Avg order value:   ${avg_order_value:,.2f}")

    save_kpi(cursor, conn, "total_orders",     total_orders,     "count")
    save_kpi(cursor, conn, "total_revenue",    total_revenue,    "USD")
    save_kpi(cursor, conn, "avg_order_value",  avg_order_value,  "USD")

# ── KPI 2: Revenue by month ──────────────────────────────────
def kpi_revenue_by_month(cursor, conn):
    print("\n── Revenue by Month ────────────────────────────────")

    cursor.execute("""
        SELECT
            order_month,
            COUNT(DISTINCT order_id)          AS orders,
            ROUND(SUM(price)::numeric, 2)     AS revenue
        FROM v_orders_complete
        WHERE order_status = 'delivered'
        GROUP BY order_month
        ORDER BY order_month;
    """)
    rows = cursor.fetchall()

    for order_month, orders, revenue in rows:
        month_str = order_month.strftime("%Y-%m")
        print(f"   {month_str}   orders: {orders:>6,}   revenue: ${revenue:>12,.2f}")
        save_kpi(cursor, conn, "monthly_orders",  orders,  "count",  "month", month_str)
        save_kpi(cursor, conn, "monthly_revenue", revenue, "USD",    "month", month_str)

# ── KPI 3: Top categories ────────────────────────────────────
def kpi_top_categories(cursor, conn):
    print("\n── Top 10 Categories by Revenue ────────────────────")

    cursor.execute("""
        SELECT
            COALESCE(product_category_name_english, 'uncategorized') AS category,
            COUNT(DISTINCT order_id)          AS orders,
            ROUND(SUM(price)::numeric, 2)     AS revenue
        FROM v_orders_complete
        WHERE order_status = 'delivered'
        GROUP BY category
        ORDER BY revenue DESC
        LIMIT 10;
    """)
    rows = cursor.fetchall()

    for category, orders, revenue in rows:
        print(f"   {category:<30} ${revenue:>12,.2f}")
        save_kpi(cursor, conn, "category_revenue", revenue, "USD", "category", category)
        save_kpi(cursor, conn, "category_orders",  orders,  "count", "category", category)

# ── KPI 4: Delivery performance ──────────────────────────────
def kpi_delivery_performance(cursor, conn):
    print("\n── Delivery Performance ────────────────────────────")

    cursor.execute("""
        SELECT
            ROUND(AVG(actual_delivery_days)::numeric, 1) AS avg_days,
            ROUND(100.0 * SUM(
                CASE WHEN actual_delivery_days <= estimated_delivery_days
                THEN 1 ELSE 0 END
            ) / COUNT(*), 1) AS on_time_pct
        FROM v_orders_complete
        WHERE order_status = 'delivered'
          AND actual_delivery_days IS NOT NULL;
    """)
    row = cursor.fetchone()
    avg_days, on_time_pct = row

    print(f"   Avg delivery days: {avg_days}")
    print(f"   On-time rate:      {on_time_pct}%")

    save_kpi(cursor, conn, "avg_delivery_days", avg_days,    "days")
    save_kpi(cursor, conn, "on_time_rate",       on_time_pct, "pct")

# ── KPI 5: Review scores ─────────────────────────────────────
def kpi_review_scores(cursor, conn):
    print("\n── Review Scores ───────────────────────────────────")

    cursor.execute("""
        SELECT
            ROUND(AVG(review_score)::numeric, 2) AS avg_score,
            COUNT(*)                              AS total_reviews
        FROM raw_order_reviews;
    """)
    row = cursor.fetchone()
    avg_score, total_reviews = row

    print(f"   Avg review score:  {avg_score}/5")
    print(f"   Total reviews:     {total_reviews:,}")

    save_kpi(cursor, conn, "avg_review_score", avg_score,    "score")
    save_kpi(cursor, conn, "total_reviews",    total_reviews, "count")

# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("AURA — KPI Engine")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    conn   = get_connection()
    cursor = conn.cursor()

    kpi_revenue_summary(cursor, conn)
    kpi_revenue_by_month(cursor, conn)
    kpi_top_categories(cursor, conn)
    kpi_delivery_performance(cursor, conn)
    kpi_review_scores(cursor, conn)

    # Count total KPIs saved
    cursor.execute("SELECT COUNT(*) FROM kpi_snapshots;")
    total = cursor.fetchone()[0]

    print("\n" + "=" * 60)
    print(f"KPI capture complete — {total:,} total snapshots in database")
    print("=" * 60)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()