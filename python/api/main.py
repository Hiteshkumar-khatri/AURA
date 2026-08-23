from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import pandas as pd
import psycopg2
import io
import os

# ── Configuration ────────────────────────────────────────────
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

app = FastAPI(title="AURA Analytics")

# ── Database connection ───────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASS
    )

# ── Home page ─────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA Analytics</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 60px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #2c3e50; }
            .subtitle { color: #666; margin-bottom: 40px; }
            .upload-box {
                background: white;
                border: 2px dashed #3498db;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
            }
            input[type=file] { margin: 20px 0; }
            button {
                background: #3498db;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover { background: #2980b9; }
        </style>
    </head>
    <body>
        <h1>AURA Analytics</h1>
        <p class="subtitle">
            Upload your CSV or Excel file and get instant analytics.
        </p>
        <div class="upload-box">
            <h2>Upload Your Data</h2>
            <p>Supports CSV and Excel (.xlsx) files</p>
            <form action="http://localhost:8000/analyze" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".csv,.xlsx" required><br>
                <button type="submit">Analyze My Data</button>
            </form>
        </div>
    </body>
    </html>
    """
# ── Analyze endpoint ──────────────────────────────────────────
@app.post("/analyze", response_class=HTMLResponse)
async def analyze(file: UploadFile = File(...)):

    # ── Read file ─────────────────────────────────────────────
    contents = await file.read()
    filename = file.filename

    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(contents))
    elif filename.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        return "<h1>Error: Please upload a CSV or Excel file.</h1>"

    # ── Profile ───────────────────────────────────────────────
    row_count      = df.shape[0]
    col_count      = df.shape[1]
    duplicate_rows = int(df.duplicated().sum())

    # ── Quality checks ────────────────────────────────────────
    findings = []
    score    = 100.0

    for col in df.columns:
        missing_pct = round(df[col].isnull().sum() / row_count * 100, 2)
        if missing_pct > 50:
            findings.append(f"⚠️ <b>{col}</b>: {missing_pct}% missing values (critical)")
            score -= 20
        elif missing_pct > 20:
            findings.append(f"⚠️ <b>{col}</b>: {missing_pct}% missing values (high)")
            score -= 10
        elif missing_pct > 5:
            findings.append(f"⚠️ <b>{col}</b>: {missing_pct}% missing values (medium)")
            score -= 5
        elif missing_pct > 0:
            findings.append(f"ℹ️ <b>{col}</b>: {missing_pct}% missing values (low)")
            score -= 1

    if duplicate_rows > 0:
        dup_pct = round(duplicate_rows / row_count * 100, 2)
        findings.append(f"⚠️ <b>{duplicate_rows:,} duplicate rows</b> ({dup_pct}%)")
        score -= 10

    score = max(round(score, 1), 0)

    # ── Numeric column stats ──────────────────────────────────
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    stats_rows   = ""
    for col in numeric_cols[:5]:
        stats_rows += f"""
        <tr>
            <td>{col}</td>
            <td>{df[col].mean():.2f}</td>
            <td>{df[col].min():.2f}</td>
            <td>{df[col].max():.2f}</td>
            <td>{df[col].isnull().sum()}</td>
        </tr>
        """

    # ── Score color ───────────────────────────────────────────
    if score >= 80:
        score_color = "#27ae60"
        score_label = "Good"
    elif score >= 60:
        score_color = "#f39c12"
        score_label = "Fair"
    else:
        score_color = "#e74c3c"
        score_label = "Poor"

    # ── Findings HTML ─────────────────────────────────────────
    findings_html = ""
    if findings:
        for f in findings:
            findings_html += f"<li>{f}</li>"
    else:
        findings_html = "<li>✅ No issues found</li>"

    # ── Column list ───────────────────────────────────────────
    cols_html = "".join(f"<span style='background:#eee;padding:3px 8px;margin:3px;border-radius:3px;display:inline-block'>{c}</span>" for c in df.columns)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA — Results</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 40px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            h1 {{ color: #2c3e50; }}
            .card {{
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin: 20px 0;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin: 20px 0;
            }}
            .metric {{
                background: white;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .metric-value {{
                font-size: 2em;
                font-weight: bold;
                color: #2c3e50;
            }}
            .metric-label {{
                color: #666;
                font-size: 0.9em;
            }}
            .score {{
                font-size: 3em;
                font-weight: bold;
                color: {score_color};
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}
            th {{ background: #f8f9fa; }}
            a {{
                background: #3498db;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <h1>AURA Analytics — Results</h1>
        <p>File: <b>{filename}</b></p>

        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{row_count:,}</div>
                <div class="metric-label">Total Rows</div>
            </div>
            <div class="metric">
                <div class="metric-value">{col_count}</div>
                <div class="metric-label">Columns</div>
            </div>
            <div class="metric">
                <div class="metric-value">{duplicate_rows:,}</div>
                <div class="metric-label">Duplicate Rows</div>
            </div>
        </div>

        <div class="card">
            <h2>Data Quality Score</h2>
            <div class="score">{score}/100</div>
            <p>{score_label} quality dataset</p>
        </div>

        <div class="card">
            <h2>Columns ({col_count})</h2>
            {cols_html}
        </div>

        <div class="card">
            <h2>Quality Findings</h2>
            <ul>{findings_html}</ul>
        </div>

        {"<div class='card'><h2>Numeric Column Statistics</h2><table><tr><th>Column</th><th>Mean</th><th>Min</th><th>Max</th><th>Missing</th></tr>" + stats_rows + "</table></div>" if stats_rows else ""}

        <br>
        <a href="/">← Analyze Another File</a>
    </body>
    </html>
    """