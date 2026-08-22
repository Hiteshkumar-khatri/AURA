import psycopg2
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from datetime import datetime

# ── Configuration ────────────────────────────────────────────
DB_HOST    = "localhost"
DB_PORT    = 5433
DB_NAME    = "aura"
DB_USER    = "aura_user"
DB_PASS    = "aura_pass"
N_SEGMENTS = 4
RANDOM_STATE = 42

# ── Connect ──────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASS
    )

# ── Build RFM table ──────────────────────────────────────────
def build_rfm(cursor):
    print("\n── Building RFM Table ──────────────────────────────")

    cursor.execute("""
        SELECT
            o.customer_id,
            MAX(o.order_purchase_timestamp)         AS last_order_date,
            COUNT(DISTINCT o.order_id)              AS frequency,
            ROUND(SUM(i.price)::numeric, 2)         AS monetary
        FROM raw_orders o
        JOIN raw_order_items i ON o.order_id = i.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY o.customer_id
        HAVING COUNT(DISTINCT o.order_id) >= 1;
    """)
    rows = cursor.fetchall()

    df = pd.DataFrame(rows, columns=[
        "customer_id", "last_order_date", "frequency", "monetary"
    ])

    # Recency = days since last order
    # We use the max date in the dataset as "today"
    reference_date = df["last_order_date"].max()
    df["recency"] = (reference_date - df["last_order_date"]).dt.days

    print(f"   Customers:     {len(df):,}")
    print(f"   Reference date: {reference_date.strftime('%Y-%m-%d')}")
    print(f"   Avg recency:   {df['recency'].mean():.0f} days")
    print(f"   Avg frequency: {df['frequency'].mean():.2f} orders")
    print(f"   Avg monetary:  ${df['monetary'].mean():.2f}")

    return df

# ── Run K-Means ──────────────────────────────────────────────
def run_kmeans(df):
    print("\n── Running K-Means Clustering ──────────────────────")

    features = df[["recency", "frequency", "monetary"]].copy()

    # Scale features so no single dimension dominates
    # Without scaling, monetary ($thousands) would overpower
    # recency (days) and frequency (small integers)
    scaler   = StandardScaler()
    scaled   = scaler.fit_transform(features)

    # Run K-Means
    kmeans = KMeans(
        n_clusters=N_SEGMENTS,
        random_state=RANDOM_STATE,
        n_init=10
    )
    df["segment"] = kmeans.fit_predict(scaled)

    print(f"   Segments created: {N_SEGMENTS}")
    print(f"   Inertia:          {kmeans.inertia_:.0f}")

    return df, kmeans, scaler

# ── Describe segments ────────────────────────────────────────
def describe_segments(df):
    print("\n── Segment Profiles ────────────────────────────────")

    summary = df.groupby("segment").agg(
        customers  = ("customer_id", "count"),
        avg_recency   = ("recency",   "mean"),
        avg_frequency = ("frequency", "mean"),
        avg_monetary  = ("monetary",  "mean"),
        total_revenue = ("monetary",  "sum"),
    ).round(1)

    segment_labels = {}

    for seg, row in summary.iterrows():
        # Label segments based on their characteristics
        if row["avg_monetary"] >= summary["avg_monetary"].median():
            value = "High Value"
        else:
            value = "Low Value"

        if row["avg_recency"] <= summary["avg_recency"].median():
            recency = "Recent"
        else:
            recency = "Lapsed"

        label = f"{value} / {recency}"
        segment_labels[seg] = label

        print(f"\n   Segment {seg} — {label}")
        print(f"     Customers:     {row['customers']:,}")
        print(f"     Avg recency:   {row['avg_recency']:.0f} days")
        print(f"     Avg frequency: {row['avg_frequency']:.2f} orders")
        print(f"     Avg spend:     ${row['avg_monetary']:.2f}")
        print(f"     Total revenue: ${row['total_revenue']:,.0f}")

    return summary, segment_labels

# ── Save results to DB ───────────────────────────────────────
def save_segments(cursor, conn, df, segment_labels):
    print("\n── Saving to Database ──────────────────────────────")

    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_customer_segments (
            segment_run_id  SERIAL,
            customer_id     VARCHAR(50),
            segment_id      INTEGER,
            segment_label   VARCHAR(100),
            recency_days    INTEGER,
            frequency       INTEGER,
            monetary        NUMERIC(10,2),
            segmented_at    TIMESTAMP DEFAULT NOW()
        );
    """)

    # Clear previous run
    cursor.execute("TRUNCATE ml_customer_segments;")
    conn.commit()

    # Insert new segments
    rows = []
    for _, row in df.iterrows():
        rows.append((
            row["customer_id"],
            int(row["segment"]),
            segment_labels[row["segment"]],
            int(row["recency"]),
            int(row["frequency"]),
            float(row["monetary"]),
        ))

    from psycopg2.extras import execute_values
    execute_values(cursor, """
        INSERT INTO ml_customer_segments
            (customer_id, segment_id, segment_label,
             recency_days, frequency, monetary)
        VALUES %s;
    """, rows)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM ml_customer_segments;")
    count = cursor.fetchone()[0]
    print(f"   ✅ {count:,} customers segmented and saved")

# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("AURA — Customer Segmentation (K-Means RFM)")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    conn   = get_connection()
    cursor = conn.cursor()

    df               = build_rfm(cursor)
    df, kmeans, _    = run_kmeans(df)
    summary, labels  = describe_segments(df)
    save_segments(cursor, conn, df, labels)

    print("\n" + "=" * 60)
    print("Segmentation complete")
    print("=" * 60)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()