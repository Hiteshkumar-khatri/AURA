import pandas as pd
import psycopg2
import os

# ── Configuration ────────────────────────────────────────────
DATA_DIR = r"D:\AURA\data\sample"
DB_HOST  = "localhost"
DB_PORT  = 5433
DB_NAME  = "aura"
DB_USER  = "aura_user"
DB_PASS  = "aura_pass"

# ── Dataset list ─────────────────────────────────────────────
DATASETS = [
    "olist_orders_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]

# ── Connect to database ──────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASS
    )

# ── Profile a single dataset ─────────────────────────────────
def profile_dataset(cursor, conn, filename):
    filepath    = os.path.join(DATA_DIR, filename)
    dataset     = filename.replace(".csv", "")

    print(f"\n── {dataset} {'─' * (50 - len(dataset))}")

    # Create job record
    cursor.execute("""
        INSERT INTO pipeline_jobs (status, dataset_name)
        VALUES ('running', %s)
        RETURNING job_id;
    """, (dataset,))
    job_id = cursor.fetchone()[0]
    conn.commit()

    # Load dataset
    print(f"   Loading...")
    df = pd.read_csv(filepath)

    # Basic stats
    row_count      = df.shape[0]
    column_count   = df.shape[1]
    duplicate_rows = int(df.duplicated().sum())

    print(f"   Rows:       {row_count:,}")
    print(f"   Columns:    {column_count}")
    print(f"   Duplicates: {duplicate_rows:,}")

    # Save dataset profile
    cursor.execute("""
        INSERT INTO dataset_profiles
            (job_id, dataset_name, row_count, column_count, duplicate_rows)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING profile_id;
    """, (job_id, dataset, int(row_count), int(column_count), duplicate_rows))
    profile_id = cursor.fetchone()[0]
    conn.commit()

    # Profile each column
    print(f"   Columns:")
    for col in df.columns:
        missing_count = int(df[col].isnull().sum())
        missing_pct   = round(missing_count / row_count * 100, 2)
        unique_count  = int(df[col].nunique())
        data_type     = str(df[col].dtype)

        flag = " ⚠️" if missing_pct > 5 else ""
        print(f"     {col:<45} missing: {missing_pct:>5}%{flag}")

        cursor.execute("""
            INSERT INTO column_profiles
                (profile_id, column_name, data_type,
                 missing_count, missing_pct, unique_count)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (profile_id, col, data_type,
              missing_count, missing_pct, unique_count))

    conn.commit()

    # Mark job complete
    cursor.execute("""
        UPDATE pipeline_jobs
        SET status      = 'completed',
            finished_at = NOW(),
            rows_input  = %s,
            rows_output = %s
        WHERE job_id = %s;
    """, (int(row_count), int(row_count), job_id))
    conn.commit()

    print(f"   ✅ Saved (job_id={job_id}, profile_id={profile_id})")
    return job_id

# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("AURA — Data Profiler")
    print("=" * 60)

    conn   = get_connection()
    cursor = conn.cursor()

    for filename in DATASETS:
        try:
            profile_dataset(cursor, conn, filename)
        except Exception as e:
            print(f"   ❌ Failed: {e}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("Profiling complete")
    print("=" * 60)

if __name__ == "__main__":
    main()