from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
import pandas as pd
import io
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

from session import (create_session, get_session, get_session_dir,
                     get_session_files, save_file_to_session)
from templates.layout import sidebar_layout

app = FastAPI(title="AURA Analytics")

# ── Helper ────────────────────────────────────────────────────
def get_or_create_session(request: Request):
    session_id = request.cookies.get("aura_session")
    if session_id and get_session(session_id):
        return session_id
    return create_session()

# ── Home ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA Analytics</title>
        <style>
            * { box-sizing:border-box; margin:0; padding:0; }
            body {
                font-family:'Segoe UI',Arial,sans-serif;
                background:#0d1117;
                min-height:100vh;
                display:flex;
                align-items:center;
                justify-content:center;
            }
            .container { text-align:center; padding:40px; max-width:600px; }
            h1 {
                font-size:3.5em;
                letter-spacing:4px;
                background:linear-gradient(90deg,#3498db,#2ecc71);
                -webkit-background-clip:text;
                -webkit-text-fill-color:transparent;
                font-weight:900;
                margin-bottom:8px;
            }
            .tagline { color:#8b949e; font-size:1em; margin-bottom:45px; }
            .upload-box {
                background:#161b22;
                border:1px solid #30363d;
                border-radius:15px;
                padding:40px 50px;
            }
            .upload-box h2 { color:#e6edf3; margin-bottom:8px; font-size:1.1em; }
            .upload-box p  { color:#8b949e; margin-bottom:20px; font-size:0.88em; }
            input[type=file] {
                color:#8b949e; margin:15px 0; display:block; width:100%;
                background:#21262d; border:1px solid #30363d;
                padding:10px; border-radius:6px;
            }
            button {
                background:linear-gradient(90deg,#3498db,#2ecc71);
                color:white; border:none; padding:13px 30px;
                border-radius:8px; cursor:pointer; font-size:0.95em;
                font-weight:700; width:100%; letter-spacing:1px; margin-top:10px;
            }
            button:hover { opacity:0.9; }
            .continue-btn {
                display:block; background:#21262d; color:#e6edf3;
                border:1px solid #30363d; padding:11px 30px;
                border-radius:8px; text-decoration:none;
                font-size:0.88em; margin-top:12px; text-align:center;
            }
            .continue-btn:hover { background:#30363d; }
            .features {
                display:grid; grid-template-columns:repeat(2,1fr);
                gap:12px; margin-top:30px;
            }
            .feature {
                background:#161b22; border:1px solid #30363d;
                border-radius:10px; padding:15px; text-align:left;
            }
            .feature-icon  { font-size:1.3em; margin-bottom:5px; }
            .feature-title { color:#e6edf3; font-weight:600; font-size:0.88em; }
            .feature-desc  { color:#8b949e; font-size:0.78em; margin-top:3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AURA</h1>
            <p class="tagline">Autonomous Unified Revenue Analytics</p>
            <div class="upload-box">
                <h2>Upload Your Data</h2>
                <p>CSV or Excel — single file or entire folder</p>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" name="files" accept=".csv,.xlsx" multiple required>
                    <button type="submit">&#9889; Start Analysis</button>
                </form>
                <a href="/manager" class="continue-btn">&#128193; Continue Previous Session</a>
            </div>
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">&#129302;</div>
                    <div class="feature-title">AI Analyst</div>
                    <div class="feature-desc">Ask questions in plain English</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">&#128202;</div>
                    <div class="feature-title">Auto Dashboard</div>
                    <div class="feature-desc">Charts generated automatically</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">&#128269;</div>
                    <div class="feature-title">Data Quality</div>
                    <div class="feature-desc">Instant quality score and findings</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">&#129529;</div>
                    <div class="feature-title">Smart Cleaning</div>
                    <div class="feature-desc">You choose exactly what to fix</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# ── Upload ────────────────────────────────────────────────────
@app.post("/upload")
async def upload(request: Request, files: list[UploadFile] = File(...)):
    session_id = get_or_create_session(request)
    for file in files:
        if not file.filename.endswith((".csv", ".xlsx")):
            continue
        contents = await file.read()
        save_file_to_session(session_id, file.filename, contents)
    response = RedirectResponse(url="/manager", status_code=303)
    response.set_cookie("aura_session", session_id, max_age=86400)
    return response

# ── File Manager ──────────────────────────────────────────────
@app.get("/manager", response_class=HTMLResponse)
def manager(request: Request):
    session_id = request.cookies.get("aura_session")
    if not session_id or not get_session(session_id):
        return RedirectResponse(url="/")

    files = get_session_files(session_id)

    file_rows    = ""
    file_options = ""
    for f in files:
        file_rows += f"""
        <tr>
            <td>&#128196; {f['name']}</td>
            <td style="color:#8b949e">{f['size_str']}</td>
            <td>
                <a href="/view/{session_id}/{f['name']}" class="btn btn-secondary" style="font-size:0.78em;padding:5px 10px">View</a>
                <a href="/analyze/{session_id}/{f['name']}" class="btn btn-primary" style="font-size:0.78em;padding:5px 10px">Analyze</a>
                <a href="/clean/{session_id}/{f['name']}" class="btn btn-warning" style="font-size:0.78em;padding:5px 10px">Clean</a>
                <a href="/delete/{session_id}/{f['name']}" class="btn btn-danger" style="font-size:0.78em;padding:5px 10px"
                   onclick="return confirm('Delete {f['name']}?')">Delete</a>
            </td>
        </tr>"""
        file_options += f'<option value="{f["name"]}">{f["name"]}</option>'

    if not files:
        file_rows = """
        <tr>
            <td colspan="3" style="text-align:center;color:#8b949e;padding:30px">
                No files yet. <a href="/" style="color:#3498db">Upload files</a>
            </td>
        </tr>"""

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#128193; My Files</h2>
            <p>{len(files)} file(s) in your session</p>
        </div>
        <div class="topbar-right">
            <a href="/ask-all/{session_id}" class="topbar-btn">&#129302; Ask AI</a>
            <a href="/" class="topbar-btn primary">+ Upload More</a>
        </div>
    </div>

    <div class="page-content">
        <div class="table-card">
            <h3>Your Files</h3>
            <table>
                <tr><th>File Name</th><th>Size</th><th>Actions</th></tr>
                {file_rows}
            </table>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
            <div class="chart-card">
                <h3>&#128279; Compare Two Files</h3>
                <p style="color:#8b949e;font-size:0.82em;margin-bottom:12px">Select two files to compare side by side</p>
                <form action="/compare/{session_id}" method="get">
                    <label style="color:#8b949e;font-size:0.8em">File A:</label>
                    <select name="file_a">{file_options}</select>
                    <label style="color:#8b949e;font-size:0.8em;margin-top:8px;display:block">File B:</label>
                    <select name="file_b">{file_options}</select>
                    <button type="submit" class="btn btn-primary" style="width:100%;margin-top:12px">Compare Files</button>
                </form>
            </div>
            <div class="chart-card">
                <h3>&#10133; Upload More Files</h3>
                <div class="upload-zone">
                    <h3>Add More Files</h3>
                    <p>CSV or Excel files</p>
                    <form action="/upload" method="post" enctype="multipart/form-data">
                        <input type="file" name="files" accept=".csv,.xlsx" multiple>
                        <button type="submit" class="btn btn-primary" style="margin-top:12px">Upload</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(sidebar_layout(content, active_page="files", session_id=session_id))

# ── View file ─────────────────────────────────────────────────
@app.get("/view/{session_id}/{filename}", response_class=HTMLResponse)
def view_file(session_id: str, filename: str):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if not os.path.exists(filepath):
        return HTMLResponse("<h1>File not found</h1>")
    df = pd.read_csv(filepath) if filename.endswith(".csv") else pd.read_excel(filepath)
    headers = "".join(f"<th>{c}</th>" for c in df.columns)
    rows    = ""
    for _, row in df.head(100).iterrows():
        rows += "<tr>" + "".join(f"<td>{v}</td>" for v in row.values) + "</tr>"

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#128196; {filename}</h2>
            <p>{len(df):,} rows x {len(df.columns)} columns — showing first 100 rows</p>
        </div>
        <div class="topbar-right">
            <a href="/manager" class="topbar-btn">&#8592; Back to Files</a>
        </div>
    </div>
    <div class="page-content">
        <div class="table-card" style="overflow-x:auto">
            <table><tr>{headers}</tr>{rows}</table>
        </div>
    </div>
    """
    return HTMLResponse(sidebar_layout(content, active_page="files", session_id=session_id))

# ── Delete file ───────────────────────────────────────────────
@app.get("/delete/{session_id}/{filename}")
def delete_file(session_id: str, filename: str):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    return RedirectResponse(url="/manager", status_code=303)

# ── Analyze file ──────────────────────────────────────────────
@app.get("/analyze/{session_id}/{filename}", response_class=HTMLResponse)
def analyze_file(session_id: str, filename: str):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if not os.path.exists(filepath):
        return HTMLResponse("<h1>File not found</h1>")

    from analyzer import load_file, profile_dataframe
    df = load_file(filepath)
    p  = profile_dataframe(df)

    score       = p["score"]
    score_color = "#2ecc71" if score >= 80 else "#f39c12" if score >= 60 else "#e74c3c"
    score_label = "Good" if score >= 80 else "Fair" if score >= 60 else "Poor"

    findings_html = "".join(
        f'<div class="finding">{f}</div>' for f in p["findings"]
    ) or "<p style='color:#8b949e'>&#10003; No issues found</p>"

    cols_html = "".join(f'<span class="tag">{c}</span>' for c in df.columns)

    checkboxes_html = ""
    for key, label in p["clean_opts"]:
        checkboxes_html += f"""
        <div class="check-item">
            <label>
                <input type="checkbox" name="fixes" value="{key}" checked>
                {label}
            </label>
        </div>"""
    if not checkboxes_html:
        checkboxes_html = "<p style='color:#8b949e'>&#10003; No cleaning needed.</p>"

    charts_html = p["time_chart_div"] + p["missing_chart_div"] + p["avg_chart_div"]
    if not charts_html:
        charts_html = "<p style='color:#8b949e;text-align:center;padding:40px'>No charts available</p>"

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#128202; {filename}</h2>
            <p>Quality Score: {score}/100 — {score_label}</p>
        </div>
        <div class="topbar-right">
            <a href="/manager" class="topbar-btn">&#8592; Files</a>
        </div>
    </div>
    <div class="page-content">
        <div class="metrics-grid" style="grid-template-columns:repeat(4,1fr)">
            <div class="metric-card">
                <div class="metric-label">Total Rows</div>
                <div class="metric-value">{p['row_count']:,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Columns</div>
                <div class="metric-value">{p['col_count']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Duplicates</div>
                <div class="metric-value">{p['duplicate_rows']:,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Quality Score</div>
                <div class="metric-value" style="color:{score_color}">{score}/100</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('overview',event)">&#128203; Overview</button>
            <button class="tab" onclick="showTab('clean',event)">&#129529; Clean</button>
            <button class="tab" onclick="showTab('dashboard',event)">&#128202; Dashboard</button>
            <button class="tab" onclick="showTab('ai',event)">&#129302; AI Insights</button>
        </div>

        <div id="overview" class="tab-content active">
            <div class="chart-card" style="margin-bottom:18px">
                <h3>Columns ({p['col_count']})</h3>
                {cols_html}
            </div>
            <div class="chart-card" style="margin-bottom:18px">
                <h3>Quality Findings</h3>
                {findings_html}
            </div>
            {"<div class='chart-card'><h3>Numeric Statistics</h3><table><tr><th>Column</th><th>Mean</th><th>Median</th><th>Min</th><th>Max</th><th>Missing</th></tr>" + p['stats_rows'] + "</table></div>" if p['stats_rows'] else ""}
        </div>

        <div id="clean" class="tab-content">
            <div class="chart-card">
                <h3>Choose What to Fix</h3>
                <p style="color:#8b949e;margin-bottom:13px;font-size:0.85em">
                    Only selected fixes will be applied to your download.
                </p>
                <form action="/download-clean/{session_id}/{filename}" method="post">
                    {checkboxes_html}
                    <br>
                    <button type="submit" class="btn btn-primary" style="margin-top:10px">
                        &#11015; Apply Fixes &amp; Download
                    </button>
                </form>
            </div>
        </div>

        <div id="dashboard" class="tab-content">
            <div class="charts-grid">
                {charts_html}
            </div>
        </div>

        <div id="ai" class="tab-content">
            <div class="chart-card" style="margin-bottom:18px">
                <h3>AI Analysis</h3>
                <div class="ai-response">
                    <ul style="padding-left:20px;list-style:none">
                        {p['ai_html']}
                    </ul>
                </div>
            </div>
            <div class="chart-card">
                <h3>Ask the AI Analyst</h3>
                <form action="/ask-file/{session_id}/{filename}" method="post">
                    <input type="text" name="question"
                           placeholder="e.g. Why did sales drop? Which product is performing best?">
                    <button type="submit" class="btn btn-primary" style="width:100%;margin-top:8px">
                        Ask AURA
                    </button>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    var chartsRendered = false;
    function showTab(name, event) {{
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById(name).classList.add('active');
        event.target.classList.add('active');
        if (name === 'dashboard' && !chartsRendered) {{
            chartsRendered = true;
            renderCharts();
        }}
    }}
    function renderCharts() {{
        {p['time_chart_js']}
        {p['missing_chart_js']}
        {p['avg_chart_js']}
    }}
    </script>
    """
    return HTMLResponse(sidebar_layout(content, active_page="dashboard", session_id=session_id))

# ── Download cleaned file ─────────────────────────────────────
@app.post("/download-clean/{session_id}/{filename}")
async def download_clean(session_id: str, filename: str,
                         fixes: list[str] = Form(default=[])):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if not os.path.exists(filepath):
        return HTMLResponse("<h1>File not found</h1>")

    from analyzer import load_file
    df = load_file(filepath)

    for fix in fixes:
        if fix == "remove_duplicates":
            df = df.drop_duplicates()
        elif fix.startswith("fill_median_"):
            col = fix.replace("fill_median_", "")
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median())
        elif fix.startswith("fill_zero_"):
            col = fix.replace("fill_zero_", "")
            if col in df.columns:
                df[col] = df[col].fillna(0)
        elif fix.startswith("fill_mode_"):
            col = fix.replace("fill_mode_", "")
            if col in df.columns:
                mode = df[col].mode()
                if len(mode) > 0:
                    df[col] = df[col].fillna(mode[0])
        elif fix.startswith("fix_date_"):
            col = fix.replace("fix_date_", "")
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    clean_name = filename.replace(".csv","_cleaned.csv").replace(".xlsx","_cleaned.csv")
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={clean_name}"}
    )

# ── Clean hub ─────────────────────────────────────────────────
@app.get("/clean/{session_id}/{filename}", response_class=HTMLResponse)
def clean_file(session_id: str, filename: str):
    return RedirectResponse(f"/analyze/{session_id}/{filename}#clean")

# ── Compare files ─────────────────────────────────────────────
@app.get("/compare/{session_id}", response_class=HTMLResponse)
def compare_files(session_id: str, file_a: str, file_b: str):
    dir_path = get_session_dir(session_id)

    def load(fname):
        path = os.path.join(dir_path, fname)
        return pd.read_csv(path) if fname.endswith(".csv") else pd.read_excel(path)

    df_a = load(file_a)
    df_b = load(file_b)

    shared_cols = list(set(df_a.columns) & set(df_b.columns))

    comparison_rows = ""
    for col in df_a.columns:
        in_b    = "&#10003;" if col in df_b.columns else "&#10007;"
        dtype_a = str(df_a[col].dtype)
        dtype_b = str(df_b[col].dtype) if col in df_b.columns else "—"
        miss_a  = f"{df_a[col].isnull().sum()/len(df_a)*100:.1f}%"
        miss_b  = f"{df_b[col].isnull().sum()/len(df_b)*100:.1f}%" if col in df_b.columns else "—"
        comparison_rows += f"<tr><td>{col}</td><td>{dtype_a}</td><td>{miss_a}</td><td>{in_b}</td><td>{dtype_b}</td><td>{miss_b}</td></tr>"

    numeric_comparison = ""
    for col in shared_cols:
        if pd.api.types.is_numeric_dtype(df_a[col]) and pd.api.types.is_numeric_dtype(df_b[col]):
            mean_a = df_a[col].mean()
            mean_b = df_b[col].mean()
            change = ((mean_b - mean_a) / mean_a * 100) if mean_a != 0 else 0
            arrow  = "&#128200;" if change > 0 else "&#128201;" if change < 0 else "&#8594;"
            color  = "#2ecc71" if change > 0 else "#e74c3c" if change < 0 else "#8b949e"
            numeric_comparison += f'<tr><td>{col}</td><td>{mean_a:.2f}</td><td>{mean_b:.2f}</td><td style="color:{color}">{arrow} {change:+.1f}%</td></tr>'

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#128279; Comparing Files</h2>
            <p>{file_a} vs {file_b}</p>
        </div>
        <div class="topbar-right">
            <a href="/manager" class="topbar-btn">&#8592; Back to Files</a>
        </div>
    </div>
    <div class="page-content">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px">
            <div class="metric-card">
                <div class="metric-label">&#128196; {file_a}</div>
                <div class="metric-value">{len(df_a):,}</div>
                <div style="color:#8b949e;font-size:0.8em">{len(df_a.columns)} columns</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">&#128196; {file_b}</div>
                <div class="metric-value">{len(df_b):,}</div>
                <div style="color:#8b949e;font-size:0.8em">{len(df_b.columns)} columns</div>
            </div>
        </div>

        <div class="chart-card" style="margin-bottom:18px">
            <h3>&#128279; Shared Columns ({len(shared_cols)})</h3>
            <p style="margin-top:8px">{"  ".join(f'<span class="tag">{c}</span>' for c in shared_cols) if shared_cols else "<span style='color:#8b949e'>No shared columns</span>"}</p>
        </div>

        {"<div class='chart-card' style='margin-bottom:18px'><h3>&#128202; Metric Comparison</h3><table><tr><th>Column</th><th>" + file_a + " (avg)</th><th>" + file_b + " (avg)</th><th>Change</th></tr>" + numeric_comparison + "</table></div>" if numeric_comparison else ""}

        <div class="chart-card">
            <h3>&#128270; Column by Column</h3>
            <table>
                <tr><th>Column</th><th>{file_a} Type</th><th>{file_a} Missing</th><th>In {file_b}?</th><th>{file_b} Type</th><th>{file_b} Missing</th></tr>
                {comparison_rows}
            </table>
        </div>
    </div>
    """
    return HTMLResponse(sidebar_layout(content, active_page="files", session_id=session_id))

# ── Ask AI about specific file ────────────────────────────────
@app.post("/ask-file/{session_id}/{filename}", response_class=HTMLResponse)
async def ask_file(session_id: str, filename: str, question: str = Form(...)):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if not os.path.exists(filepath):
        return HTMLResponse("<h1>File not found</h1>")

    from analyzer import load_file
    from analytics.ai_analyst import answer_question

    df           = load_file(filepath)
    row_count    = df.shape[0]
    col_count    = df.shape[1]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    findings = [f"{col}: {round(df[col].isnull().sum()/row_count*100,2)}% missing"
                for col in df.columns if df[col].isnull().sum() > 0]

    numeric_stats = "".join(
        f"{col}: mean={df[col].mean():.2f}, min={df[col].min():.2f}, max={df[col].max():.2f}\n"
        for col in numeric_cols[:5]
    )

    date_col = next((col for col in df.columns
                     if any(kw in col.lower() for kw in ["date","time","month","year"])), None)

    answer = answer_question(
        question=question, filename=filename,
        row_count=row_count, col_count=col_count,
        findings=findings, numeric_stats=numeric_stats,
        columns=list(df.columns), date_col=date_col
    )

    answer_html = ""
    for line in answer.split("\n"):
        line = line.strip()
        if not line:
            answer_html += "<br>"
        elif line.startswith("- ") or line.startswith("* "):
            answer_html += f"<li style='margin-bottom:6px'>{line[2:]}</li>"
        elif line.startswith("**") and line.endswith("**"):
            answer_html += f"<h3 style='margin:15px 0 8px;color:#e6edf3'>{line.replace('**','')}</h3>"
        else:
            answer_html += f"<p style='margin-bottom:8px'>{line}</p>"

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#129302; AI Analyst</h2>
            <p>{filename}</p>
        </div>
        <div class="topbar-right">
            <a href="/analyze/{session_id}/{filename}" class="topbar-btn">&#8592; Back to Analysis</a>
        </div>
    </div>
    <div class="page-content">
        <div class="chart-card">
            <h3>Your Question</h3>
            <div style="background:#0d1117;padding:14px;border-radius:8px;
                        margin-bottom:18px;font-style:italic;color:#8b949e;
                        border-left:3px solid #3498db">
                "{question}"
            </div>
            <h3>AURA's Answer</h3>
            <div class="ai-response" style="margin-top:12px">
                <ul style="padding-left:20px;list-style:none">
                    {answer_html}
                </ul>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(sidebar_layout(content, active_page="chat", session_id=session_id))

# ── Ask AI about all files ────────────────────────────────────
@app.get("/ask-all/{session_id}", response_class=HTMLResponse)
def ask_all(session_id: str):
    files = get_session_files(session_id)
    file_list = "".join(f"<li>{f['name']} — {f['size_str']}</li>" for f in files)

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#129302; Chat with AURA</h2>
            <p>Ask about all your files</p>
        </div>
        <div class="topbar-right">
            <a href="/manager" class="topbar-btn">&#8592; Files</a>
        </div>
    </div>
    <div class="page-content">
        <div class="chart-card">
            <h3>Files in context</h3>
            <ul style="color:#8b949e;font-size:0.85em;padding-left:20px;margin-top:8px">
                {file_list}
            </ul>
        </div>
        <div class="chart-card">
            <h3>Ask a question</h3>
            <p style="color:#8b949e;font-size:0.85em;margin-bottom:12px">
                Select a file and ask your question
            </p>
            <form action="/ask-file/{session_id}/placeholder" method="post">
                <input type="text" name="question"
                       placeholder="e.g. Find patterns in my data, Why did sales drop?">
                <button type="submit" class="btn btn-primary" style="width:100%;margin-top:8px">
                    Ask AURA
                </button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(sidebar_layout(content, active_page="chat", session_id=session_id))

# ── Placeholder routes for sidebar nav ───────────────────────
@app.get("/dashboard/{session_id}", response_class=HTMLResponse)
def dashboard(session_id: str):
    return RedirectResponse(f"/manager")

@app.get("/quality/{session_id}", response_class=HTMLResponse)
def quality(session_id: str):
    files = get_session_files(session_id)
    if not files:
        return RedirectResponse("/manager")

    from analyzer import load_file, profile_dataframe

    all_quality = ""
    overall_scores = []

    for f in files:
        df = load_file(f["path"])
        p  = profile_dataframe(df)
        score = p["score"]
        overall_scores.append(score)
        score_color = "#2ecc71" if score >= 80 else "#f39c12" if score >= 60 else "#e74c3c"

        findings_html = "".join(
            f'<div class="finding">{finding}</div>'
            for finding in p["findings"]
        ) or "<p style='color:#8b949e'>&#10003; No issues found</p>"

        all_quality += f"""
        <div class="chart-card" style="margin-bottom:18px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
                <h3>&#128196; {f['name']}</h3>
                <span style="font-size:1.4em;font-weight:700;color:{score_color}">{score}/100</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:15px">
                <div style="background:#0d1117;padding:12px;border-radius:8px;text-align:center">
                    <div style="color:#8b949e;font-size:0.75em">Rows</div>
                    <div style="font-weight:700;font-size:1.1em">{p['row_count']:,}</div>
                </div>
                <div style="background:#0d1117;padding:12px;border-radius:8px;text-align:center">
                    <div style="color:#8b949e;font-size:0.75em">Columns</div>
                    <div style="font-weight:700;font-size:1.1em">{p['col_count']}</div>
                </div>
                <div style="background:#0d1117;padding:12px;border-radius:8px;text-align:center">
                    <div style="color:#8b949e;font-size:0.75em">Duplicates</div>
                    <div style="font-weight:700;font-size:1.1em">{p['duplicate_rows']:,}</div>
                </div>
            </div>
            {findings_html}
            <div style="margin-top:12px">
                <a href="/analyze/{session_id}/{f['name']}" class="btn btn-primary" style="font-size:0.82em">
                    Full Analysis &#8594;
                </a>
                <a href="/clean/{session_id}/{f['name']}" class="btn btn-secondary" style="font-size:0.82em">
                    Clean This File
                </a>
            </div>
        </div>"""

    avg_score = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0
    avg_color = "#2ecc71" if avg_score >= 80 else "#f39c12" if avg_score >= 60 else "#e74c3c"

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#128269; Data Quality</h2>
            <p>Quality report for all {len(files)} file(s)</p>
        </div>
        <div class="topbar-right">
            <a href="/manager" class="topbar-btn">&#8592; Files</a>
        </div>
    </div>
    <div class="page-content">
        <div class="metrics-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:22px">
            <div class="metric-card">
                <div class="metric-label">Files Analyzed</div>
                <div class="metric-value">{len(files)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Average Quality Score</div>
                <div class="metric-value" style="color:{avg_color}">{avg_score}/100</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Files Needing Attention</div>
                <div class="metric-value" style="color:#e74c3c">
                    {sum(1 for s in overall_scores if s < 80)}
                </div>
            </div>
        </div>
        {all_quality}
    </div>
    """
    return HTMLResponse(sidebar_layout(content, active_page="quality", session_id=session_id))

@app.get("/kpis/{session_id}", response_class=HTMLResponse)
def kpis(session_id: str):
    files = get_session_files(session_id)
    if not files:
        return RedirectResponse("/manager")

    from analyzer import load_file

    kpi_cards = ""
    charts_html = ""
    chart_js = ""

    for f in files:
        df           = load_file(f["path"])
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        row_count    = len(df)

        if not numeric_cols:
            continue

        # Key metrics
        metrics_html = ""
        for col in numeric_cols[:6]:
            total  = df[col].sum()
            mean   = df[col].mean()
            mx     = df[col].max()
            mn     = df[col].min()
            metrics_html += f"""
            <div class="metric-card">
                <div class="metric-label">{col}</div>
                <div class="metric-value" style="font-size:1.3em">{mean:,.2f}</div>
                <div class="metric-change neutral">
                    avg &nbsp;|&nbsp; min: {mn:,.2f} &nbsp;|&nbsp; max: {mx:,.2f}
                </div>
            </div>"""

        # Date-based trend
        date_col = next((col for col in df.columns
                         if any(kw in col.lower()
                                for kw in ["date","time","month","year"])), None)

        trend_html = ""
        if date_col and numeric_cols:
            df_c = df.copy()
            df_c[date_col] = pd.to_datetime(df_c[date_col], errors="coerce")
            target = numeric_cols[0]
            ts = df_c.groupby(df_c[date_col].dt.to_period("M"))[target].sum().dropna()
            if len(ts) > 1:
                ts_labels = [str(p) for p in ts.index]
                ts_values = [round(float(v), 2) for v in ts.values]
                chart_id  = f"kpi_chart_{f['name'].replace('.','_')}"
                trend_html = f"<div class='chart-card' style='margin-top:18px'><h3>{target} Trend</h3><canvas id='{chart_id}'></canvas></div>"
                chart_js  += f"""
                new Chart(document.getElementById('{chart_id}'), {{
                    type: 'line',
                    data: {{
                        labels: {ts_labels},
                        datasets: [{{
                            label: '{target}',
                            data: {ts_values},
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52,152,219,0.1)',
                            fill: true, tension: 0.3
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{ legend: {{ labels: {{ color: '#e6edf3' }} }} }},
                        scales: {{
                            x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
                            y: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
                        }}
                    }}
                }});"""

        kpi_cards += f"""
        <div class="chart-card" style="margin-bottom:22px">
            <h3>&#128196; {f['name']}</h3>
            <div class="metrics-grid" style="margin-top:15px">
                {metrics_html}
            </div>
            {trend_html}
        </div>"""

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#128200; KPIs &amp; Metrics</h2>
            <p>Key performance indicators from your data</p>
        </div>
        <div class="topbar-right">
            <a href="/manager" class="topbar-btn">&#8592; Files</a>
        </div>
    </div>
    <div class="page-content">
        {kpi_cards if kpi_cards else "<div class='chart-card'><p style='color:#8b949e'>No numeric columns found in uploaded files.</p></div>"}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>{chart_js}</script>
    """
    return HTMLResponse(sidebar_layout(content, active_page="kpis", session_id=session_id))

@app.get("/anomalies/{session_id}", response_class=HTMLResponse)
def anomalies_page(session_id: str):
    files = get_session_files(session_id)
    if not files:
        return RedirectResponse("/manager")

    from analyzer import load_file
    import statistics

    def z_scores(values):
        if len(values) < 3:
            return []
        avg = statistics.mean(values)
        std = statistics.stdev(values)
        if std == 0:
            return [(v, 0.0, avg) for v in values]
        return [(v, (v - avg) / std, avg) for v in values]

    all_anomalies = ""
    total_found   = 0

    for f in files:
        df           = load_file(f["path"])
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        anomaly_rows = ""
        file_count   = 0

        for col in numeric_cols[:5]:
            values = df[col].dropna().tolist()
            scored = z_scores(values)
            for val, z, avg in scored:
                if abs(z) >= 2.0:
                    severity = "critical" if abs(z) >= 3.0 else "high" if abs(z) >= 2.5 else "medium"
                    color    = "#e74c3c" if severity == "critical" else "#e67e22" if severity == "high" else "#f1c40f"
                    direction = "above" if z > 0 else "below"
                    anomaly_rows += f"""
                    <tr>
                        <td>{col}</td>
                        <td>{val:,.2f}</td>
                        <td>{avg:,.2f}</td>
                        <td>{z:+.2f}</td>
                        <td><span class="badge" style="background:rgba(231,76,60,0.15);color:{color}">{severity}</span></td>
                        <td style="color:#8b949e;font-size:0.82em">{abs(z):.1f} std devs {direction} average</td>
                    </tr>"""
                    file_count += 1
                    if file_count >= 20:
                        break
            if file_count >= 20:
                break

        total_found += file_count
        all_anomalies += f"""
        <div class="chart-card" style="margin-bottom:18px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
                <h3>&#128196; {f['name']}</h3>
                <span class="badge {'badge-red' if file_count > 0 else 'badge-green'}">
                    {file_count} anomaly(ies) found
                </span>
            </div>
            {"<table><tr><th>Column</th><th>Value</th><th>Expected Avg</th><th>Z-Score</th><th>Severity</th><th>Description</th></tr>" + anomaly_rows + "</table>" if anomaly_rows else "<p style='color:#8b949e'>&#10003; No anomalies detected</p>"}
        </div>"""

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#128680; Anomaly Detection</h2>
            <p>Unusual patterns detected in your data</p>
        </div>
        <div class="topbar-right">
            <a href="/manager" class="topbar-btn">&#8592; Files</a>
        </div>
    </div>
    <div class="page-content">
        <div class="metric-card" style="margin-bottom:22px;display:inline-block;padding:18px 30px">
            <div class="metric-label">Total Anomalies Found</div>
            <div class="metric-value" style="color:{'#e74c3c' if total_found > 0 else '#2ecc71'}">{total_found}</div>
        </div>
        {all_anomalies}
    </div>
    """
    return HTMLResponse(sidebar_layout(content, active_page="anomalies", session_id=session_id))

@app.get("/segments/{session_id}", response_class=HTMLResponse)
def segments(session_id: str):
    return RedirectResponse(f"/manager")

@app.get("/clean-hub/{session_id}", response_class=HTMLResponse)
def clean_hub(session_id: str):
    return RedirectResponse(f"/manager")

@app.get("/reports/{session_id}", response_class=HTMLResponse)
def reports(session_id: str):
    files = get_session_files(session_id)
    if not files:
        return RedirectResponse("/manager")

    from analyzer import load_file, profile_dataframe
    from datetime import datetime

    report_sections = ""
    all_scores      = []
    total_rows      = 0
    total_cols      = 0
    all_findings    = []

    for f in files:
        df = load_file(f["path"])
        p  = profile_dataframe(df)
        all_scores.append(p["score"])
        total_rows += p["row_count"]
        total_cols += p["col_count"]
        all_findings.extend(p["findings"])

        score_color = "#2ecc71" if p["score"] >= 80 else "#f39c12" if p["score"] >= 60 else "#e74c3c"

        stats_section = ""
        if p["stats_rows"]:
            stats_section = f"""
            <h4 style="color:#8b949e;font-size:0.82em;margin:12px 0 8px">Numeric Statistics</h4>
            <table style="font-size:0.82em">
                <tr><th>Column</th><th>Mean</th><th>Median</th><th>Min</th><th>Max</th><th>Missing</th></tr>
                {p['stats_rows']}
            </table>"""

        findings_section = "".join(
            f'<div style="padding:6px 0;border-bottom:1px solid #21262d;font-size:0.85em">{finding}</div>'
            for finding in p["findings"]
        ) or "<p style='color:#8b949e;font-size:0.85em'>No issues found</p>"

        report_sections += f"""
        <div style="margin-bottom:25px;padding-bottom:25px;border-bottom:1px solid #30363d">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <h3 style="color:#e6edf3">&#128196; {f['name']}</h3>
                <span style="font-weight:700;color:{score_color}">Quality: {p['score']}/100</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px">
                <div style="background:#0d1117;padding:10px;border-radius:6px;text-align:center">
                    <div style="color:#8b949e;font-size:0.72em">Rows</div>
                    <div style="font-weight:600">{p['row_count']:,}</div>
                </div>
                <div style="background:#0d1117;padding:10px;border-radius:6px;text-align:center">
                    <div style="color:#8b949e;font-size:0.72em">Columns</div>
                    <div style="font-weight:600">{p['col_count']}</div>
                </div>
                <div style="background:#0d1117;padding:10px;border-radius:6px;text-align:center">
                    <div style="color:#8b949e;font-size:0.72em">Duplicates</div>
                    <div style="font-weight:600">{p['duplicate_rows']:,}</div>
                </div>
            </div>
            <h4 style="color:#8b949e;font-size:0.82em;margin-bottom:8px">Quality Findings</h4>
            {findings_section}
            {stats_section}
        </div>"""

    avg_score   = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    avg_color   = "#2ecc71" if avg_score >= 80 else "#f39c12" if avg_score >= 60 else "#e74c3c"
    report_date = datetime.now().strftime("%B %d, %Y at %H:%M")

    content = f"""
    <div class="topbar">
        <div class="topbar-left">
            <h2>&#128209; Reports</h2>
            <p>Generated {report_date}</p>
        </div>
        <div class="topbar-right">
            <a href="/manager" class="topbar-btn">&#8592; Files</a>
        </div>
    </div>
    <div class="page-content">
        <div class="chart-card" style="margin-bottom:22px">
            <h3>Executive Summary</h3>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:15px">
                <div style="background:#0d1117;padding:15px;border-radius:8px;text-align:center">
                    <div style="color:#8b949e;font-size:0.75em">Files Analyzed</div>
                    <div style="font-size:1.6em;font-weight:700">{len(files)}</div>
                </div>
                <div style="background:#0d1117;padding:15px;border-radius:8px;text-align:center">
                    <div style="color:#8b949e;font-size:0.75em">Total Rows</div>
                    <div style="font-size:1.6em;font-weight:700">{total_rows:,}</div>
                </div>
                <div style="background:#0d1117;padding:15px;border-radius:8px;text-align:center">
                    <div style="color:#8b949e;font-size:0.75em">Total Columns</div>
                    <div style="font-size:1.6em;font-weight:700">{total_cols}</div>
                </div>
                <div style="background:#0d1117;padding:15px;border-radius:8px;text-align:center">
                    <div style="color:#8b949e;font-size:0.75em">Avg Quality Score</div>
                    <div style="font-size:1.6em;font-weight:700;color:{avg_color}">{avg_score}/100</div>
                </div>
            </div>
            <div style="margin-top:18px;padding:15px;background:#0d1117;border-radius:8px;
                        border-left:3px solid #3498db">
                <p style="color:#e6edf3;font-size:0.9em;line-height:1.6">
                    This report covers <b>{len(files)} file(s)</b> containing
                    <b>{total_rows:,} total rows</b> across <b>{total_cols} columns</b>.
                    The average data quality score is <b style="color:{avg_color}">{avg_score}/100</b>.
                    {f'<b style="color:#e74c3c">{sum(1 for s in all_scores if s < 80)} file(s) need attention.</b>' if any(s < 80 for s in all_scores) else '<b style="color:#2ecc71">All files are in good quality.</b>'}
                </p>
            </div>
        </div>

        <div class="chart-card">
            <h3>Detailed File Reports</h3>
            <div style="margin-top:18px">
                {report_sections}
            </div>
        </div>
    </div>
    """
    return HTMLResponse(sidebar_layout(content, active_page="reports", session_id=session_id))

@app.get("/chat/{session_id}", response_class=HTMLResponse)
def chat(session_id: str):
    return RedirectResponse(f"/ask-all/{session_id}")