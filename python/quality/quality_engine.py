import psycopg2

# ── Configuration ────────────────────────────────────────────
DB_HOST = "localhost"
DB_PORT = 5433
DB_NAME = "aura"
DB_USER = "aura_user"
DB_PASS = "aura_pass"

# ── Severity levels ──────────────────────────────────────────
# These thresholds determine how serious a problem is.
# Critical = pipeline should probably stop
# High     = significant problem, needs attention
# Medium   = notable but manageable
# Low      = minor, informational

MISSING_THRESHOLDS = {
    "critical": 50.0,
    "high":     20.0,
    "medium":    5.0,
    "low":       0.0,
}

DUPLICATE_THRESHOLDS = {
    "critical": 20.0,
    "high":     10.0,
    "medium":    1.0,
    "low":       0.0,
}

# ── Known acceptable high-missing columns ────────────────────
# These columns are expected to have high missing values.
# We still flag them but don't penalize the score heavily.
EXPECTED_MISSING = {
    "olist_order_reviews_dataset": [
        "review_comment_title",
        "review_comment_message",
    ]
}

# ── Known column name typos ──────────────────────────────────
KNOWN_TYPOS = {
    "product_name_lenght":        "product_name_length",
    "product_description_lenght": "product_description_length",
}

# ── Connect ──────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASS
    )

# ── Get severity for missing % ───────────────────────────────
def missing_severity(pct):
    if pct >= MISSING_THRESHOLDS["critical"]:
        return "critical"
    elif pct >= MISSING_THRESHOLDS["high"]:
        return "high"
    elif pct >= MISSING_THRESHOLDS["medium"]:
        return "medium"
    elif pct > 0:
        return "low"
    return None

# ── Get severity for duplicate % ────────────────────────────
def duplicate_severity(pct):
    if pct >= DUPLICATE_THRESHOLDS["critical"]:
        return "critical"
    elif pct >= DUPLICATE_THRESHOLDS["high"]:
        return "high"
    elif pct >= DUPLICATE_THRESHOLDS["medium"]:
        return "medium"
    elif pct > 0:
        return "low"
    return None

# ── Save a finding ───────────────────────────────────────────
def save_finding(cursor, conn, profile_id, run_id, dataset_name,
                 column_name, finding_type, severity,
                 description, affected_rows, affected_pct):
    cursor.execute("""
        INSERT INTO quality_findings
            (profile_id, run_id, dataset_name, column_name,
             finding_type, severity, description,
             affected_rows, affected_pct)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (profile_id, run_id, dataset_name, column_name,
          finding_type, severity, description,
          affected_rows, affected_pct))
    conn.commit()

# ── Calculate quality score ──────────────────────────────────
def calculate_score(findings):
    # Start at 100, deduct points per finding
    score = 100.0
    deductions = {
        "critical": 25.0,
        "high":     10.0,
        "medium":    5.0,
        "low":       1.0,
    }
    for finding in findings:
        severity = finding["severity"]
        # Expected missing columns get half deduction
        if finding.get("expected"):
            score -= deductions[severity] / 2
        else:
            score -= deductions[severity]

    return max(round(score, 2), 0.0)  # Never below 0

# ── Check one dataset ────────────────────────────────────────
def check_dataset(cursor, conn, profile_id, run_id,
                  dataset_name, row_count, duplicate_rows, columns):

    print(f"\n── {dataset_name} {'─' * (50 - len(dataset_name))}")
    findings = []

    # ── Check 1: Duplicates ──────────────────────────────────
    if duplicate_rows > 0:
        dup_pct  = round(duplicate_rows / row_count * 100, 2)
        severity = duplicate_severity(dup_pct)
        desc     = f"{duplicate_rows:,} duplicate rows ({dup_pct}% of dataset)"
        print(f"   ⚠️  DUPLICATES [{severity.upper()}]: {desc}")
        save_finding(cursor, conn, profile_id, run_id, dataset_name,
                     None, "duplicate_rows", severity, desc,
                     duplicate_rows, dup_pct)
        findings.append({"severity": severity, "expected": False})

    # ── Check 2: Missing values per column ───────────────────
    expected_cols = EXPECTED_MISSING.get(dataset_name, [])

    for col in columns:
        col_name    = col["column_name"]
        missing_pct = float(col["missing_pct"])
        missing_cnt = col["missing_count"]

        severity = missing_severity(missing_pct)
        if severity is None:
            continue

        is_expected = col_name in expected_cols
        tag = " (expected behavior)" if is_expected else ""

        desc = (f"{col_name}: {missing_pct}% missing "
                f"({missing_cnt:,} rows){tag}")
        print(f"   ⚠️  MISSING [{severity.upper()}]: {desc}")

        save_finding(cursor, conn, profile_id, run_id, dataset_name,
                     col_name, "missing_values", severity, desc,
                     missing_cnt, missing_pct)
        findings.append({"severity": severity, "expected": is_expected})

    # ── Check 3: Column name typos ───────────────────────────
    for col in columns:
        col_name = col["column_name"]
        if col_name in KNOWN_TYPOS:
            correct = KNOWN_TYPOS[col_name]
            desc    = f"Column '{col_name}' appears to be a typo — should be '{correct}'"
            print(f"   ⚠️  TYPO [MEDIUM]: {desc}")
            save_finding(cursor, conn, profile_id, run_id, dataset_name,
                         col_name, "column_name_typo", "medium", desc,
                         None, None)
            findings.append({"severity": "medium", "expected": False})

    # ── Check 4: Date columns stored as text ─────────────────
    date_keywords = ["date", "timestamp", "time"]
    for col in columns:
        col_name  = col["column_name"]
        data_type = col["data_type"]
        is_date_name = any(kw in col_name.lower() for kw in date_keywords)
        is_text_type = data_type in ("object", "str")

        if is_date_name and is_text_type:
            desc = (f"Column '{col_name}' appears to be a date "
                    f"but is stored as text ({data_type})")
            print(f"   ⚠️  DATE AS TEXT [MEDIUM]: {desc}")
            save_finding(cursor, conn, profile_id, run_id, dataset_name,
                         col_name, "date_as_text", "medium", desc,
                         None, None)
            findings.append({"severity": "medium", "expected": False})

    # ── Score ─────────────────────────────────────────────────
    if not findings:
        print(f"   ✅ No issues found")

    score = calculate_score(findings)

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f["severity"]] += 1

    cursor.execute("""
        INSERT INTO quality_scores
            (profile_id, run_id, dataset_name, score,
             total_findings, critical_findings,
             high_findings, medium_findings, low_findings)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (profile_id, run_id, dataset_name, score,
          len(findings),
          counts["critical"], counts["high"],
          counts["medium"], counts["low"]))
    conn.commit()

    print(f"   Quality score: {score}/100")
    return score

# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("AURA — Data Quality Engine")
    print("=" * 60)

    conn   = get_connection()
    cursor = conn.cursor()

    # Get latest profiling run
    cursor.execute("""
        SELECT run_id FROM profiling_runs
        WHERE status = 'completed'
        ORDER BY run_id DESC LIMIT 1;
    """)
    result = cursor.fetchone()
    if not result:
        print("❌ No completed profiling run found. Run profiler first.")
        return

    run_id = result[0]
    print(f"\nUsing profiling Run ID: {run_id}")

    # Get all dataset profiles for this run
    cursor.execute("""
        SELECT profile_id, dataset_name, row_count, duplicate_rows
        FROM dataset_profiles
        WHERE run_id = %s
        ORDER BY profile_id;
    """, (run_id,))
    profiles = cursor.fetchall()

    scores = []

    for profile_id, dataset_name, row_count, duplicate_rows in profiles:

        # Get column profiles for this dataset
        cursor.execute("""
            SELECT column_name, data_type, missing_count, missing_pct
            FROM column_profiles
            WHERE profile_id = %s
            ORDER BY column_profile_id;
        """, (profile_id,))
        columns = [
            {
                "column_name":  row[0],
                "data_type":    row[1],
                "missing_count": row[2],
                "missing_pct":  row[3],
            }
            for row in cursor.fetchall()
        ]

        score = check_dataset(
            cursor, conn,
            profile_id, run_id,
            dataset_name, row_count, duplicate_rows,
            columns
        )
        scores.append((dataset_name, score))

    # ── Summary ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Quality Score Summary")
    print("=" * 60)
    for name, score in scores:
        bar   = "█" * int(score / 5)
        grade = "✅" if score >= 80 else "⚠️ " if score >= 60 else "❌"
        print(f"  {grade} {name:<45} {score:>6}/100  {bar}")

    avg = round(sum(s for _, s in scores) / len(scores), 2)
    print(f"\n  Average quality score: {avg}/100")
    print("=" * 60)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()