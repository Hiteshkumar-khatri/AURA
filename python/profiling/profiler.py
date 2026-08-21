import pandas as pd
import psycopg2
from datetime import datetime

# ── Configuration ────────────────────────────────────────────
FILE        = r"D:\AURA\data\sample\olist_orders_dataset.csv"
DATASET     = "olist_orders_dataset"
DB_HOST     = "localhost"
DB_PORT     = 5433
DB_NAME     = "aura"
DB_USER     = "aura_user"
DB_PASS     = "aura_pass"

# ── Connect to database ──────────────────────────────────────
print("Connecting to database...")
conn = psycopg2.connect(
    host=DB_HOST, port=DB_PORT,
    database=DB_NAME, user=DB_USER, password=DB_PASS
)
conn.autocommit = False
cursor = conn.cursor()

# ── Create pipeline job ──────────────────────────────────────
print("Creating pipeline job...")
cursor.execute("""
    INSERT INTO pipeline_jobs (status, dataset_name)
    VALUES ('running', %s)
    RETURNING job_id;
""", (DATASET,))
job_id = cursor.fetchone()[0]
conn.commit()
print(f"   Job ID: {job_id}")

# ── Load dataset ─────────────────────────────────────────────
print(f"Loading {DATASET}...")
df = pd.read_csv(FILE)

# ── Profile dataset ──────────────────────────────────────────
print("Profiling dataset...")
row_count      = df.shape[0]
column_count   = df.shape[1]
duplicate_rows = df.duplicated().sum()

print(f"\n── Dataset Overview ────────────────────────────────")
print(f"   Rows:            {row_count:,}")
print(f"   Columns:         {column_count}")
print(f"   Duplicate rows:  {duplicate_rows:,}")

# ── Save dataset profile ─────────────────────────────────────
cursor.execute("""
    INSERT INTO dataset_profiles
        (job_id, dataset_name, row_count, column_count, duplicate_rows)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING profile_id;
""", (job_id, DATASET, int(row_count), int(column_count), int(duplicate_rows)))
profile_id = cursor.fetchone()[0]
conn.commit()

# ── Profile each column ──────────────────────────────────────
print(f"\n── Column Profiles ─────────────────────────────────")
for col in df.columns:
    missing_count = int(df[col].isnull().sum())
    missing_pct   = round(missing_count / row_count * 100, 2)
    unique_count  = int(df[col].nunique())
    data_type     = str(df[col].dtype)

    print(f"   {col:<40} missing: {missing_count:>5} ({missing_pct}%)   unique: {unique_count:,}")

    cursor.execute("""
        INSERT INTO column_profiles
            (profile_id, column_name, data_type,
             missing_count, missing_pct, unique_count)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (profile_id, col, data_type,
          missing_count, missing_pct, unique_count))

conn.commit()

# ── Mark job complete ────────────────────────────────────────
cursor.execute("""
    UPDATE pipeline_jobs
    SET status      = 'completed',
        finished_at = NOW(),
        rows_input  = %s,
        rows_output = %s
    WHERE job_id = %s;
""", (int(row_count), int(row_count), job_id))
conn.commit()

print(f"\n✅ Profile saved to database")
print(f"   Job ID:     {job_id}")
print(f"   Profile ID: {profile_id}")

# ── Clean up ─────────────────────────────────────────────────
cursor.close()
conn.close()