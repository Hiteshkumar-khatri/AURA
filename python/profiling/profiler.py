import pandas as pd

# ── Configuration ────────────────────────────────────────────
FILE = r"D:\AURA\data\sample\olist_orders_dataset.csv"

# ── Load ─────────────────────────────────────────────────────
print("Loading dataset...")
df = pd.read_csv(FILE)

# ── Basic shape ──────────────────────────────────────────────
print("\n── Dataset Overview ────────────────────────────────")
print(f"Rows:       {df.shape[0]:,}")
print(f"Columns:    {df.shape[1]}")

# ── Column names ─────────────────────────────────────────────
print("\n── Columns ─────────────────────────────────────────")
for col in df.columns:
    print(f"  {col}")

# ── Data types ───────────────────────────────────────────────
print("\n── Data Types ──────────────────────────────────────")
for col, dtype in df.dtypes.items():
    print(f"  {col:<40} {dtype}")

# ── Missing values ───────────────────────────────────────────
print("\n── Missing Values ──────────────────────────────────")
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(2)
for col in df.columns:
    print(f"  {col:<40} {missing[col]:>6} missing  ({missing_pct[col]}%)")

# ── Duplicate rows ───────────────────────────────────────────
dupes = df.duplicated().sum()
print(f"\n── Duplicate Rows ──────────────────────────────────")
print(f"  {dupes:,} duplicate rows")

# ── Categorical columns: value counts ────────────────────────
print("\n── order_status Values ─────────────────────────────")
status_counts = df["order_status"].value_counts()
for status, count in status_counts.items():
    pct = round(count / len(df) * 100, 1)
    print(f"  {status:<30} {count:>6,}  ({pct}%)")

print("\n── Done ────────────────────────────────────────────")