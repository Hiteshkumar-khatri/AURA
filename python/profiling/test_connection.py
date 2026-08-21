import psycopg2

# ── Connection settings ──────────────────────────────────────
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="aura",
    user="aura_user",
    password="aura_pass"
)

print("✅ Connected to PostgreSQL successfully")

# ── Check PostgreSQL version ─────────────────────────────────
cursor = conn.cursor()
cursor.execute("SELECT version();")
version = cursor.fetchone()
print(f"   Version: {version[0]}")

# ── Clean up ─────────────────────────────────────────────────
cursor.close()
conn.close()
print("✅ Connection closed cleanly")