import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
import sys

# Windows consoles default to cp1252, which can't encode the emoji /
# box-drawing characters used in the output below. Reconfigure to UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

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
def load_table(cursor, conn, filename, table_name, columns, transform=None, truncate=False):
    filepath = os.path.join(DATA_DIR, filename)

    print(f"\n── Loading {table_name} {'─' * (40 - len(table_name))}")
    print(f"   Reading {filename}...")

    if truncate:
        cursor.execute(f"TRUNCATE {table_name};")
        conn.commit()
        print(f"   Truncated {table_name}")

    df = pd.read_csv(filepath)

    # Apply transformation if provided
    if transform:
        df = transform(df)

    # Select only the columns we need
    df = df[columns]

    # Replace NaN with None so PostgreSQL gets NULL
    df = df.where(pd.notnull(df), None)
    df = df.replace({pd.NaT: None})

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
        ],
        truncate = True
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

    # ── Orders ───────────────────────────────────────────────
    date_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]

    def transform_orders(df):
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    load_table(
        cursor, conn,
        filename   = "olist_orders_dataset.csv",
        table_name = "raw_orders",
        columns    = [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
        transform = transform_orders
    )

    # ── Order Items ──────────────────────────────────────────
    def transform_order_items(df):
        df["shipping_limit_date"] = pd.to_datetime(
            df["shipping_limit_date"], errors="coerce"
        )
        df["shipping_limit_date"] = df["shipping_limit_date"].replace({pd.NaT: None})
        return df

    load_table(
        cursor, conn,
        filename   = "olist_order_items_dataset.csv",
        table_name = "raw_order_items",
        columns    = [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
        transform = transform_order_items,
        truncate = True
    )

    # ── Order Reviews ────────────────────────────────────────
    def transform_reviews(df):
        for col in ["review_creation_date", "review_answer_timestamp"]:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df[col] = df[col].replace({pd.NaT: None})
        return df

    load_table(
        cursor, conn,
        filename   = "olist_order_reviews_dataset.csv",
        table_name = "raw_order_reviews",
        columns    = [
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ],
        transform = transform_reviews,
        truncate = True
    )

    # ── Products ─────────────────────────────────────────────
    # Note: column name typos kept intentionally in raw table.
    # They will be fixed in the cleaned/transformed table later.
    def transform_products(df):
        int_cols = [
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
        ]
        for col in int_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].where(pd.notnull(df[col]), None)
        return df

    load_table(
        cursor, conn,
        filename   = "olist_products_dataset.csv",
        table_name = "raw_products",
        columns    = [
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ],
        transform = transform_products
    )

    print("\n" + "=" * 60)
    print("Ingestion complete")
    print("=" * 60)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()