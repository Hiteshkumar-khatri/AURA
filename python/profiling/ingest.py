import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os

# ── Configuration ────────────────────────────────────────────
DATA_DIR = r"D:\AURA\data\sample"
DB_HOST  = "localhost"
DB_PORT  = 5433
DB_NAME  = "aura"
DB_USER  = "aura_user"
DB_PASS  = "aura_pass"

# ── Connect ──────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASS
    )

# ── Generic loader ───────────────────────────────────────────
def load_table(cursor, conn, filename, table_name, columns, transform=None):
    filepath = os.path.join(DATA_DIR, filename)

    print(f"\n── Loading {table_name} {'─' * (40 - len(table_name))}")
    print(f"   Reading {filename}...")

    df = pd.read_csv(filepath)

    # Apply transformation if provided
    if transform:
        df = transform(df)

    # Select only the columns we need
    df = df[columns]

    # Replace NaN with None so PostgreSQL gets NULL
    df = df.where(pd.notnull(df), None)

    rows = [tuple(row) for row in df.itertuples(index=False)]

    print(f"   Inserting {len(rows):,} rows into {table_name}...")

    col_str = ", ".join(columns)
    query   = f"INSERT INTO {table_name} ({col_str}) VALUES %s ON CONFLICT DO NOTHING;"

    execute_values(cursor, query, rows)
    conn.commit()

    # Verify
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    print(f"   ✅ {count:,} rows now in {table_name}")

# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("AURA — Data Ingestion")
    print("=" * 60)

    conn   = get_connection()
    cursor = conn.cursor()

    # ── Customers ────────────────────────────────────────────
    load_table(
        cursor, conn,
        filename   = "olist_customers_dataset.csv",
        table_name = "raw_customers",
        columns    = [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ]
    )

    # ── Sellers ──────────────────────────────────────────────
    load_table(
        cursor, conn,
        filename   = "olist_sellers_dataset.csv",
        table_name = "raw_sellers",
        columns    = [
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ]
    )

    # ── Order Payments ───────────────────────────────────────
    load_table(
        cursor, conn,
        filename   = "olist_order_payments_dataset.csv",
        table_name = "raw_order_payments",
        columns    = [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ]
    )

    # ── Category Translation ─────────────────────────────────
    load_table(
        cursor, conn,
        filename   = "product_category_name_translation.csv",
        table_name = "raw_category_translation",
        columns    = [
            "product_category_name",
            "product_category_name_english",
        ]
    )

    print("\n" + "=" * 60)
    print("Ingestion complete")
    print("=" * 60)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()