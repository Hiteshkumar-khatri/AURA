import psycopg2

# ── Connection ───────────────────────────────────────────────
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="aura",
    user="aura_user",
    password="aura_pass"
)
conn.autocommit = True
cursor = conn.cursor()

# ── Read and run the SQL file ────────────────────────────────
sql_file = r"D:\AURA\sql\schema\001_create_metadata_tables.sql"

print("Running schema setup...")

with open(sql_file, "r") as f:
    sql = f.read()

cursor.execute(sql)
print("✅ Tables created successfully")

# ── Verify tables exist ──────────────────────────────────────
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")

tables = cursor.fetchall()
print("\nTables in database:")
for table in tables:
    print(f"  {table[0]}")

# ── Clean up ─────────────────────────────────────────────────
cursor.close()
conn.close()
print("\n✅ Done")