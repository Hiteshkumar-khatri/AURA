from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
import pandas as pd
import io
import os
import sys
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# ── Temporary storage ─────────────────────────────────────────
TEMP_FILES = {}
AGENTS     = {}  # stores AnalystAgent per session for conversation context

app = FastAPI(title="AURA Analytics")

# ── Home page ─────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA Analytics</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container { text-align: center; padding: 40px; }
            h1 { color: white; font-size: 3em; margin-bottom: 10px; letter-spacing: 3px; }
            .tagline { color: #a0aec0; font-size: 1.1em; margin-bottom: 50px; }
            .upload-box {
                background: rgba(255,255,255,0.05);
                border: 2px dashed rgba(255,255,255,0.3);
                border-radius: 15px;
                padding: 50px 60px;
                backdrop-filter: blur(10px);
            }
            .upload-box h2 { color: white; margin-bottom: 10px; }
            .upload-box p { color: #a0aec0; margin-bottom: 25px; }
            input[type=file] { color: white; margin: 15px 0; display: block; width: 100%; }
            button {
                background: linear-gradient(90deg, #3498db, #2ecc71);
                color: white; border: none; padding: 15px 40px;
                border-radius: 8px; cursor: pointer; font-size: 16px;
                font-weight: bold; margin-top: 15px; width: 100%;
                letter-spacing: 1px;
            }
            button:hover { opacity: 0.9; }
            .features {
                display: grid; grid-template-columns: repeat(4, 1fr);
                gap: 20px; margin-top: 40px; max-width: 800px;
            }
            .feature {
                background: rgba(255,255,255,0.05);
                border-radius: 10px; padding: 20px; color: white;
            }
            .feature-icon { font-size: 2em; margin-bottom: 8px; }
            .feature-title { font-weight: bold; margin-bottom: 5px; }
            .feature-desc { color: #a0aec0; font-size: 0.85em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AURA</h1>
            <p class="tagline">Autonomous Unified Revenue Analytics</p>
            <div class="upload-box">
                <h2>Upload Your Data</h2>
                <p>Upload one file or multiple related files — AURA analyzes them together</p>
                <form action="http://localhost:8000/analyze"
                      method="post" enctype="multipart/form-data">
                    <input type="file" name="files"
                           accept=".csv,.xlsx" multiple required>
                    <button type="submit">⚡ Analyze My Data</button>
                </form>
            </div>
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">🔍</div>
                    <div class="feature-title">Smart Profiling</div>
                    <div class="feature-desc">Instant quality score</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🧹</div>
                    <div class="feature-title">Data Cleaning</div>
                    <div class="feature-desc">You choose what to fix</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <div class="feature-title">Auto Dashboard</div>
                    <div class="feature-desc">Charts from your data</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🤖</div>
                    <div class="feature-title">AI Analyst</div>
                    <div class="feature-desc">Ask questions in English</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# ── Analyze endpoint ──────────────────────────────────────────
@app.post("/analyze", response_class=HTMLResponse)
async def analyze(files: list[UploadFile] = File(...)):

    # ── Read all uploaded files ───────────────────────────────
    dataframes = {}
    for file in files:
        contents = await file.read()
        fname    = file.filename
        try:
            if fname.endswith(".csv"):
                dataframes[fname] = pd.read_csv(io.BytesIO(contents))
            elif fname.endswith(".xlsx"):
                dataframes[fname] = pd.read_excel(io.BytesIO(contents))
        except Exception as e:
            return HTMLResponse(f"<h1>Error reading {fname}: {e}</h1>")

    if not dataframes:
        return HTMLResponse("<h1>No valid files uploaded.</h1>")

    file_names = list(dataframes.keys())
    scenario   = "single"

    if len(dataframes) > 1:
        all_cols = [set(df.columns) for df in dataframes.values()]
        if len(set(frozenset(c) for c in all_cols)) == 1:
            scenario = "stack"
        else:
            col_sets = {fname: set(df.columns) for fname, df in dataframes.items()}
            fnames   = list(col_sets.keys())
            shared   = {}
            for i in range(len(fnames)):
                for j in range(i+1, len(fnames)):
                    common  = col_sets[fnames[i]] & col_sets[fnames[j]]
                    id_cols = [c for c in common if any(k in c.lower() for k in ["id","key","code"])]
                    if id_cols:
                        shared[(fnames[i], fnames[j])] = id_cols
            if shared:
                scenario = "relational"

    filename          = ", ".join(file_names)
    relationship_info = ""

    if scenario == "single":
        df       = list(dataframes.values())[0]
        filename = file_names[0]

    elif scenario == "stack":
        df       = pd.concat(list(dataframes.values()), ignore_index=True)
        filename = f"{len(dataframes)} files stacked"
        relationship_info = f"""
        <div class="card" style="border-left:4px solid #2ecc71">
            <h2>📂 Multiple Files — Same Structure</h2>
            <p>AURA stacked all files into one combined dataset.</p>
            <ul>{"".join(f"<li>{f} — {len(dataframes[f]):,} rows</li>" for f in file_names)}</ul>
            <p><b>Combined: {sum(len(d) for d in dataframes.values()):,} total rows</b></p>
        </div>"""

    elif scenario == "relational":
        base_fname = max(dataframes, key=lambda f: len(dataframes[f]))
        df         = dataframes[base_fname].copy()
        joined     = [base_fname]
        for fname, fdf in dataframes.items():
            if fname == base_fname:
                continue
            common  = set(df.columns) & set(fdf.columns)
            id_cols = [c for c in common if any(k in c.lower() for k in ["id","key","code"])]
            if id_cols:
                join_col = id_cols[0]
                new_cols = [c for c in fdf.columns if c not in df.columns or c == join_col]
                df       = df.merge(fdf[new_cols], on=join_col, how="left")
                joined.append(fname)
        filename = f"{len(joined)} related files joined"
        relationship_info = f"""
        <div class="card" style="border-left:4px solid #3498db">
            <h2>🔗 Related Files — Auto Joined</h2>
            <p>AURA found shared ID columns and joined the files.</p>
            <ul>{"".join(f"<li>{f} — {len(dataframes[f]):,} rows</li>" for f in joined)}</ul>
            <p><b>Result: {len(df):,} rows, {len(df.columns)} columns</b></p>
        </div>"""

    # Store for later
    session_id = str(uuid.uuid4())
    TEMP_FILES[session_id] = {"df": df.copy(), "filename": file_names[0]}

    # ── Profile ───────────────────────────────────────────────
    row_count      = df.shape[0]
    col_count      = df.shape[1]
    duplicate_rows = int(df.duplicated().sum())
    numeric_cols   = df.select_dtypes(include="number").columns.tolist()
    text_cols      = df.select_dtypes(include="object").columns.tolist()

    # ── Quality checks ────────────────────────────────────────
    findings   = []
    score      = 100.0
    clean_opts = []

    for col in df.columns:
        missing_cnt = int(df[col].isnull().sum())
        missing_pct = round(missing_cnt / row_count * 100, 2)
        if missing_pct > 50:
            findings.append(f"🔴 <b>{col}</b>: {missing_pct}% missing (critical)")
            score -= 20
        elif missing_pct > 20:
            findings.append(f"🟠 <b>{col}</b>: {missing_pct}% missing (high)")
            score -= 10
        elif missing_pct > 5:
            findings.append(f"🟡 <b>{col}</b>: {missing_pct}% missing (medium)")
            score -= 5
        elif missing_pct > 0:
            findings.append(f"🔵 <b>{col}</b>: {missing_pct}% missing (low)")
            score -= 1

    if duplicate_rows > 0:
        dup_pct = round(duplicate_rows / row_count * 100, 2)
        findings.append(f"🟠 <b>{duplicate_rows:,} duplicate rows</b> ({dup_pct}%)")
        score -= 10
        clean_opts.append(("remove_duplicates", f"Remove {duplicate_rows:,} duplicate rows"))

    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            clean_opts.append((f"fill_median_{col}", f"Fill missing in <b>{col}</b> with median ({df[col].median():.2f})"))
            clean_opts.append((f"fill_zero_{col}",   f"Fill missing in <b>{col}</b> with zero"))

    for col in text_cols:
        if df[col].isnull().sum() > 0:
            mode = df[col].mode()
            if len(mode) > 0:
                clean_opts.append((f"fill_mode_{col}", f"Fill missing in <b>{col}</b> with '{mode[0]}'"))

    date_cols_found = []
    for col in df.columns:
        if any(kw in col.lower() for kw in ["date","time","month","year"]):
            if df[col].dtype == object:
                clean_opts.append((f"fix_date_{col}", f"Convert <b>{col}</b> to proper date format"))
                date_cols_found.append(col)

    score = max(round(score, 1), 0)

    if score >= 80:
        score_color = "#27ae60"
        score_label = "Good"
    elif score >= 60:
        score_color = "#f39c12"
        score_label = "Fair"
    else:
        score_color = "#e74c3c"
        score_label = "Poor"

    # ── Numeric stats ─────────────────────────────────────────
    stats_rows        = ""
    numeric_stats_txt = ""
    for col in numeric_cols[:6]:
        stats_rows += f"""<tr>
            <td>{col}</td>
            <td>{df[col].mean():.2f}</td>
            <td>{df[col].median():.2f}</td>
            <td>{df[col].min():.2f}</td>
            <td>{df[col].max():.2f}</td>
            <td>{int(df[col].isnull().sum())}</td>
        </tr>"""
        numeric_stats_txt += f"{col}: mean={df[col].mean():.2f}, min={df[col].min():.2f}, max={df[col].max():.2f}\n"

    # ── Detect date column ────────────────────────────────────
    date_col = None
    df_c     = df.copy()
    for col in df_c.columns:
        if any(kw in col.lower() for kw in ["date","time","month","year"]):
            try:
                df_c[col] = pd.to_datetime(df_c[col], errors="coerce")
                if df_c[col].notna().sum() > 0:
                    date_col = col
                    break
            except:
                pass

    # ── Time series chart ─────────────────────────────────────
    time_chart_div = ""
    time_chart_js  = ""
    if date_col and numeric_cols:
        target = numeric_cols[0]
        ts     = df_c.groupby(df_c[date_col].dt.to_period("M"))[target].sum().dropna()
        if len(ts) > 1:
            ts_labels      = [str(p) for p in ts.index]
            ts_values      = [round(float(v), 2) for v in ts.values]
            time_chart_div = f"<div class='chart-box'><h3>{target} Over Time</h3><canvas id='timeChart'></canvas></div>"
            time_chart_js  = f"""
            new Chart(document.getElementById('timeChart'), {{
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
                options: {{ responsive: true }}
            }});"""

    # ── Missing chart ─────────────────────────────────────────
    missing_labels    = []
    missing_values    = []
    missing_chart_div = ""
    missing_chart_js  = ""
    for col in df.columns:
        pct = round(df[col].isnull().sum() / row_count * 100, 2)
        if pct > 0:
            missing_labels.append(col)
            missing_values.append(pct)
    if missing_labels:
        missing_chart_div = "<div class='chart-box'><h3>Missing Values (%)</h3><canvas id='missingChart'></canvas></div>"
        missing_chart_js  = f"""
        new Chart(document.getElementById('missingChart'), {{
            type: 'bar',
            data: {{
                labels: {missing_labels},
                datasets: [{{ label: 'Missing %', data: {missing_values}, backgroundColor: '#e74c3c' }}]
            }},
            options: {{ responsive: true }}
        }});"""

    # ── Averages chart ────────────────────────────────────────
    avg_labels    = numeric_cols[:6]
    avg_values    = [round(float(df[c].mean()), 2) for c in avg_labels]
    avg_chart_div = ""
    avg_chart_js  = ""
    if avg_labels:
        avg_chart_div = "<div class='chart-box'><h3>Column Averages</h3><canvas id='avgChart'></canvas></div>"
        avg_chart_js  = f"""
        new Chart(document.getElementById('avgChart'), {{
            type: 'bar',
            data: {{
                labels: {avg_labels},
                datasets: [{{ label: 'Average', data: {avg_values}, backgroundColor: '#2ecc71' }}]
            }},
            options: {{ responsive: true }}
        }});"""

    # ── AI Analysis via Agent ─────────────────────────────────
    from analytics.analyst_agent import AnalystAgent
    agent = AnalystAgent(df, filename)
    AGENTS[session_id] = agent
    ai_insights = agent.get_initial_analysis()

    ai_html = ""
    for line in ai_insights.split("\n"):
        line = line.strip()
        if not line:
            ai_html += "<br>"
        elif line.startswith("**") and line.endswith("**"):
            ai_html += f"<h3 style='margin:15px 0 8px'>{line.replace('**','')}</h3>"
        elif line.startswith("- ") or line.startswith("* "):
            ai_html += f"<li style='margin-bottom:6px'>{line[2:]}</li>"
        else:
            ai_html += f"<p style='margin-bottom:8px'>{line}</p>"

    # ── Build HTML ────────────────────────────────────────────
    checkboxes_html = ""
    for key, label in clean_opts:
        checkboxes_html += f"""
        <div class="check-item">
            <label>
                <input type="checkbox" name="fixes" value="{key}" checked>
                {label}
            </label>
        </div>"""
    if not checkboxes_html:
        checkboxes_html = "<p>✅ No cleaning needed.</p>"

    findings_html = ""
    for f in findings:
        findings_html += f'<div class="finding">{f}</div>'
    if not findings_html:
        findings_html = "<p>✅ No issues found</p>"

    cols_html = "".join(f'<span class="tag">{c}</span>' for c in df.columns)

    charts_html = time_chart_div + missing_chart_div + avg_chart_div
    if not charts_html:
        charts_html = "<p style='color:#888;text-align:center;padding:40px'>No charts available for this dataset</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA — Results</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; color: #2c3e50; }}
            .header {{
                background: linear-gradient(135deg, #1a1a2e, #0f3460);
                color: white; padding: 20px 40px;
                display: flex; align-items: center; justify-content: space-between;
            }}
            .header h1 {{ font-size: 1.5em; letter-spacing: 2px; }}
            .header p {{ color: #a0aec0; font-size: 0.9em; }}
            .back-btn {{
                background: rgba(255,255,255,0.1); color: white;
                padding: 8px 16px; border-radius: 5px;
                text-decoration: none; font-size: 0.9em;
            }}
            .main {{ max-width: 1200px; margin: 0 auto; padding: 30px 20px; }}
            .metrics {{
                display: grid; grid-template-columns: repeat(4, 1fr);
                gap: 15px; margin-bottom: 25px;
            }}
            .metric {{
                background: white; border-radius: 10px; padding: 20px;
                text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            .metric-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
            .metric-label {{ color: #888; font-size: 0.85em; margin-top: 5px; }}
            .score-value {{ color: {score_color}; }}
            .tabs {{
                display: flex; gap: 5px; margin-bottom: 20px;
                border-bottom: 2px solid #ddd;
            }}
            .tab {{
                padding: 12px 25px; cursor: pointer;
                border-radius: 8px 8px 0 0; background: #e8e8e8;
                border: none; font-size: 0.95em; font-weight: 500; color: #666;
            }}
            .tab.active {{
                background: white; color: #3498db;
                border-bottom: 2px solid white; margin-bottom: -2px;
            }}
            .tab-content {{ display: none; }}
            .tab-content.active {{ display: block; }}
            .card {{
                background: white; border-radius: 10px; padding: 25px;
                margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            .card h2 {{
                font-size: 1.1em; margin-bottom: 15px; color: #2c3e50;
                border-bottom: 2px solid #3498db; padding-bottom: 8px;
            }}
            .finding {{ padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 0.95em; }}
            .tag {{
                background: #eef2ff; color: #3498db; padding: 4px 10px;
                margin: 3px; border-radius: 20px; display: inline-block; font-size: 0.85em;
            }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; font-size: 0.9em; }}
            th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
            .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .chart-box {{
                background: white; border-radius: 10px; padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            .chart-box h3 {{ font-size: 0.95em; color: #555; margin-bottom: 15px; }}
            .check-item {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; }}
            .check-item label {{ display: flex; align-items: center; gap: 12px; cursor: pointer; font-size: 0.95em; }}
            .check-item input {{ width: 18px; height: 18px; cursor: pointer; }}
            .btn {{
                display: inline-block; padding: 12px 25px; border-radius: 8px;
                border: none; cursor: pointer; font-size: 0.95em; font-weight: 600;
                text-decoration: none; margin: 5px;
            }}
            .btn-green {{ background: #27ae60; color: white; }}
            .btn-blue  {{ background: #3498db; color: white; }}
            input[type=text] {{
                width: 100%; padding: 12px; border: 1px solid #ddd;
                border-radius: 8px; font-size: 1em; margin-bottom: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1>AURA Analytics</h1>
                <p>📄 {filename}</p>
            </div>
            <a href="/" class="back-btn">← New File</a>
        </div>

        <div class="main">
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
                <div class="metric">
                    <div class="metric-value score-value">{score}/100</div>
                    <div class="metric-label">Quality Score</div>
                </div>
            </div>

            <div class="tabs">
                <button class="tab active" onclick="showTab('overview', event)">📋 Overview</button>
                <button class="tab" onclick="showTab('clean', event)">🧹 Clean Data</button>
                <button class="tab" onclick="showTab('dashboard', event)">📊 Dashboard</button>
                <button class="tab" onclick="showTab('ai', event)">🤖 AI Insights</button>
            </div>

            <div id="overview" class="tab-content active">
                {relationship_info}
                <div class="card">
                    <h2>Columns ({col_count})</h2>
                    {cols_html}
                </div>
                <div class="card">
                    <h2>Quality Findings</h2>
                    {findings_html}
                </div>
                {"<div class='card'><h2>Numeric Statistics</h2><table><tr><th>Column</th><th>Mean</th><th>Median</th><th>Min</th><th>Max</th><th>Missing</th></tr>" + stats_rows + "</table></div>" if stats_rows else ""}
            </div>

            <div id="clean" class="tab-content">
                <div class="card">
                    <h2>Choose What to Fix</h2>
                    <p style="color:#888;margin-bottom:15px;font-size:0.9em">
                        Only selected fixes will be applied to your download.
                    </p>
                    <form action="http://localhost:8000/download/{session_id}" method="post">
                        {checkboxes_html}
                        <br>
                        <button type="submit" class="btn btn-green">
                            ⬇ Apply Selected Fixes & Download
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
                <div class="card">
                    <h2>AI Analysis</h2>
                    <div style="background:#f8f9ff;border-left:4px solid #8e44ad;
                                padding:20px;border-radius:0 10px 10px 0;line-height:1.7">
                        <ul style="padding-left:20px;list-style:none">
                            {ai_html}
                        </ul>
                    </div>
                </div>
                <div class="card">
                    <h2>Ask the AI Analyst</h2>
                    <p style="color:#888;margin-bottom:15px;font-size:0.9em">
                        Ask any question about your data in plain English.
                    </p>
                    <form action="http://localhost:8000/ask/{session_id}" method="post">
                        <input type="text" name="question"
                               placeholder="e.g. Why did sales drop? Which product is best?">
                        <button type="submit" class="btn btn-blue" style="width:100%">
                            Ask AURA
                        </button>
                    </form>
                </div>
            </div>
        </div>

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
            {time_chart_js}
            {missing_chart_js}
            {avg_chart_js}
        }}
        </script>
    </body>
    </html>
    """

# ── Download with selected fixes ──────────────────────────────
@app.post("/download/{session_id}")
async def download(session_id: str, fixes: list[str] = Form(default=[])):
    if session_id not in TEMP_FILES:
        return HTMLResponse("<h1>Session expired. Please re-upload.</h1>")

    data     = TEMP_FILES[session_id]
    df       = data["df"].copy()
    filename = data["filename"]
    changes  = []

    for fix in fixes:
        if fix == "remove_duplicates":
            before = len(df)
            df     = df.drop_duplicates()
            changes.append(f"Removed {before - len(df)} duplicate rows")

        elif fix.startswith("fill_median_"):
            col = fix.replace("fill_median_", "")
            if col in df.columns:
                median_val = df[col].median()
                filled     = int(df[col].isnull().sum())
                df[col]    = df[col].fillna(median_val)
                changes.append(f"Filled {filled} missing in '{col}' with median ({median_val:.2f})")

        elif fix.startswith("fill_zero_"):
            col = fix.replace("fill_zero_", "")
            if col in df.columns:
                filled  = int(df[col].isnull().sum())
                df[col] = df[col].fillna(0)
                changes.append(f"Filled {filled} missing in '{col}' with zero")

        elif fix.startswith("fill_mode_"):
            col = fix.replace("fill_mode_", "")
            if col in df.columns:
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    filled  = int(df[col].isnull().sum())
                    df[col] = df[col].fillna(mode_val[0])
                    changes.append(f"Filled {filled} missing in '{col}' with '{mode_val[0]}'")

        elif fix.startswith("fix_date_"):
            col = fix.replace("fix_date_", "")
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
                changes.append(f"Converted '{col}' to proper date format")

    output     = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    clean_name = filename.replace(".csv","_cleaned.csv").replace(".xlsx","_cleaned.csv")

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={clean_name}"}
    )

# ── Ask AI a question ─────────────────────────────────────────
@app.post("/ask/{session_id}", response_class=HTMLResponse)
async def ask(session_id: str, question: str = Form(...)):
    if session_id not in TEMP_FILES:
        return HTMLResponse("<h1>Session expired. Please re-upload.</h1>")

    from analytics.analyst_agent import AnalystAgent

    # Use existing agent if available (preserves conversation history)
    if session_id in AGENTS:
        agent = AGENTS[session_id]
    else:
        data     = TEMP_FILES[session_id]
        agent    = AnalystAgent(data["df"], data["filename"])
        AGENTS[session_id] = agent

    result   = agent.answer(question)
    answer   = result["answer"]
    plan     = result["plan"]
    audit    = result["audit_trail"]

    # Build plan HTML
    plan_html = ""
    for step in plan:
        plan_html += f"<li><code>{step['tool']}({step.get('params', {})})</code></li>"

    # Build audit trail HTML
    audit_html = ""
    for entry in audit[-5:]:
        audit_html += f"<li>{entry['time']} — <b>{entry['tool']}</b>: {entry['result']}</li>"

    answer_html = ""
    for line in answer.split("\n"):
        line = line.strip()
        if not line:
            answer_html += "<br>"
        elif line.startswith("- ") or line.startswith("* "):
            answer_html += f"<li style='margin-bottom:6px'>{line[2:]}</li>"
        elif line.startswith("**") and line.endswith("**"):
            answer_html += f"<h3 style='margin:15px 0 8px'>{line.replace('**','')}</h3>"
        elif line.startswith("|"):
            answer_html += f"<p style='font-family:monospace;font-size:0.85em'>{line}</p>"
        else:
            answer_html += f"<p style='margin-bottom:8px'>{line}</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA — AI Answer</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif;
                   max-width: 900px; margin: 40px auto;
                   padding: 20px; background: #f0f2f5; }}
            .card {{ background: white; border-radius: 10px;
                    padding: 25px; margin: 20px 0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
            h1 {{ color: #2c3e50; margin-bottom: 20px; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #8e44ad;
                 padding-bottom: 8px; margin-bottom: 15px; }}
            h3 {{ color: #2c3e50; margin: 15px 0 8px; }}
            .question {{ background: #f0f2f5; padding: 15px;
                        border-radius: 8px; margin-bottom: 20px;
                        font-style: italic; color: #555; }}
            .answer {{ background: #f8f9ff;
                      border-left: 4px solid #8e44ad;
                      padding: 20px; border-radius: 0 10px 10px 0;
                      line-height: 1.7; }}
            .plan-box {{ background: #f0fff4;
                        border-left: 4px solid #27ae60;
                        padding: 15px; border-radius: 0 8px 8px 0;
                        margin-bottom: 15px; }}
            .audit-box {{ background: #fff8f0;
                         border-left: 4px solid #f39c12;
                         padding: 15px; border-radius: 0 8px 8px 0; }}
            .btn {{ display: inline-block; background: #3498db;
                   color: white; padding: 10px 20px;
                   border-radius: 8px; text-decoration: none; margin: 5px; }}
            .btn-gray {{ background: #95a5a6; }}
            code {{ background: #f0f0f0; padding: 2px 6px;
                   border-radius: 3px; font-size: 0.85em; }}
            ul {{ padding-left: 20px; }}
        </style>
    </head>
    <body>
        <h1>🤖 AURA AI Analyst</h1>

        <div class="card">
            <h2>Your Question</h2>
            <div class="question">"{question}"</div>

            <h2>Analysis Plan</h2>
            <div class="plan-box">
                <p style="color:#27ae60;font-size:0.9em;margin-bottom:8px">
                    Tools AURA ran to answer your question:
                </p>
                <ul>{plan_html}</ul>
            </div>

            <h2>AURA's Answer</h2>
            <div class="answer">
                <ul style="list-style:none;padding-left:0">
                    {answer_html}
                </ul>
            </div>
        </div>

        <div class="card">
            <h2>Audit Trail</h2>
            <div class="audit-box">
                <p style="color:#f39c12;font-size:0.9em;margin-bottom:8px">
                    Every calculation AURA ran — nothing invented:
                </p>
                <ul>{audit_html if audit_html else '<li>No tool calls recorded</li>'}</ul>
            </div>
        </div>

        <a href="javascript:history.back()" class="btn btn-gray">← Back</a>
        <a href="/" class="btn">Upload New File</a>
    </body>
    </html>
    """
