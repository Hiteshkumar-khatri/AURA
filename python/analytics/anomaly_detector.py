import psycopg2
import statistics
from datetime import datetime

# ── Configuration ────────────────────────────────────────────
DB_HOST = "localhost"
DB_PORT = 5433
DB_NAME = "aura"
DB_USER = "aura_user"
DB_PASS = "aura_pass"

# ── Z-score threshold ────────────────────────────────────────
# Values with abs(z_score) above this are flagged as anomalies.
# 2.0 = flags roughly top/bottom 5% of values
Z_THRESHOLD = 2.0

# ── Connect ──────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASS
    )

# ── Calculate z-scores ───────────────────────────────────────
def z_scores(values):
    if len(values) < 3:
        return []
    avg = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return [(v, 0.0, avg) for v in values]
    return [(v, (v - avg) / std, avg) for v in values]

# ── Save anomaly ─────────────────────────────────────────────
def save_anomaly(cursor, conn, anomaly_type, dimension,
                 dimension_value, metric_name, observed,
                 expected, z_score, description):

    if abs(z_score) >= 3.0:
        severity = "critical"
    elif abs(z_score) >= 2.5:
        severity = "high"
    else:
        severity = "medium"

    cursor.execute("""
        INSERT INTO anomaly_findings
            (anomaly_type, dimension, dimension_value,
             metric_name, observed_value, expected_value,
             z_score, severity, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (anomaly_type, dimension, dimension_value,
          metric_name, observed, expected,
          round(z_score, 4), severity, description))
    conn.commit()

# ── Detect 1: Monthly revenue anomalies ─────────────────────
def detect_revenue_anomalies(cursor, conn):
    print("\n── Monthly Revenue Anomalies ────────────────────────")

    cursor.execute("""
        SELECT
            order_month,
            ROUND(SUM(price)::numeric, 2) AS revenue
        FROM v_orders_complete
        WHERE order_status = 'delivered'
        GROUP BY order_month
        ORDER BY order_month;
    """)
    rows = cursor.fetchall()

    months   = [r[0] for r in rows]
    revenues = [float(r[1]) for r in rows]

    scored = z_scores(revenues)
    anomalies_found = 0

    for i, (revenue, z, avg) in enumerate(scored):
        month_str = months[i].strftime("%Y-%m")
        if abs(z) >= Z_THRESHOLD:
            direction = "above" if z > 0 else "below"
            desc = (f"Monthly revenue of ${revenue:,.0f} is {abs(z):.2f} "
                    f"standard deviations {direction} average "
                    f"(avg: ${avg:,.0f})")
            print(f"   ⚠️  {month_str}: ${revenue:>12,.0f}  z={z:+.2f}  [{desc[:50]}...]")
            save_anomaly(cursor, conn,
                        "revenue_anomaly", "month", month_str,
                        "monthly_revenue", revenue, avg, z, desc)
            anomalies_found += 1

    if anomalies_found == 0:
        print("   ✅ No revenue anomalies detected")
    else:
        print(f"   {anomalies_found} anomaly(ies) detected")

# ── Detect 2: Category revenue anomalies ────────────────────
def detect_category_anomalies(cursor, conn):
    print("\n── Category Revenue Anomalies ───────────────────────")

    cursor.execute("""
        SELECT
            COALESCE(product_category_name_english, 'uncategorized') AS category,
            ROUND(SUM(price)::numeric, 2) AS revenue
        FROM v_orders_complete
        WHERE order_status = 'delivered'
        GROUP BY category
        ORDER BY revenue DESC;
    """)
    rows = cursor.fetchall()

    categories = [r[0] for r in rows]
    revenues   = [float(r[1]) for r in rows]

    scored = z_scores(revenues)
    anomalies_found = 0

    for i, (revenue, z, avg) in enumerate(scored):
        if abs(z) >= Z_THRESHOLD:
            direction = "above" if z > 0 else "below"
            desc = (f"Category '{categories[i]}' revenue of ${revenue:,.0f} "
                    f"is {abs(z):.2f} std devs {direction} average "
                    f"(avg: ${avg:,.0f})")
            print(f"   ⚠️  {categories[i]:<30} ${revenue:>10,.0f}  z={z:+.2f}")
            save_anomaly(cursor, conn,
                        "category_anomaly", "category", categories[i],
                        "category_revenue", revenue, avg, z, desc)
            anomalies_found += 1

    if anomalies_found == 0:
        print("   ✅ No category anomalies detected")
    else:
        print(f"   {anomalies_found} anomaly(ies) detected")

# ── Detect 3: Delivery time anomalies by state ───────────────
def detect_delivery_anomalies(cursor, conn):
    print("\n── Delivery Time Anomalies by State ─────────────────")

    cursor.execute("""
        SELECT
            customer_state,
            ROUND(AVG(actual_delivery_days)::numeric, 1) AS avg_days
        FROM v_orders_complete
        WHERE order_status = 'delivered'
          AND actual_delivery_days IS NOT NULL
        GROUP BY customer_state
        HAVING COUNT(*) >= 50
        ORDER BY avg_days DESC;
    """)
    rows = cursor.fetchall()

    states = [r[0] for r in rows]
    days   = [float(r[1]) for r in rows]

    scored = z_scores(days)
    anomalies_found = 0

    for i, (day_val, z, avg) in enumerate(scored):
        if abs(z) >= Z_THRESHOLD:
            direction = "slower" if z > 0 else "faster"
            desc = (f"State {states[i]} avg delivery of {day_val:.1f} days "
                    f"is {abs(z):.2f} std devs {direction} than average "
                    f"(avg: {avg:.1f} days)")
            print(f"   ⚠️  {states[i]}: {day_val:.1f} days  z={z:+.2f}  ({direction} than avg)")
            save_anomaly(cursor, conn,
                        "delivery_anomaly", "state", states[i],
                        "avg_delivery_days", day_val, avg, z, desc)
            anomalies_found += 1

    if anomalies_found == 0:
        print("   ✅ No delivery anomalies detected")
    else:
        print(f"   {anomalies_found} anomaly(ies) detected")

# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("AURA — Anomaly Detector")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    conn   = get_connection()
    cursor = conn.cursor()

    detect_revenue_anomalies(cursor, conn)
    detect_category_anomalies(cursor, conn)
    detect_delivery_anomalies(cursor, conn)

    # Summary
    cursor.execute("SELECT COUNT(*), severity FROM anomaly_findings GROUP BY severity ORDER BY severity;")
    rows = cursor.fetchall()

    print("\n── Anomaly Summary ─────────────────────────────────")
    total = 0
    for count, severity in rows:
        print(f"   {severity:<10} {count}")
        total += count
    print(f"   {'TOTAL':<10} {total}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("Anomaly detection complete")
    print("=" * 60)

if __name__ == "__main__":
    main()