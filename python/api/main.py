from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
import pandas as pd
import io
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from session import (create_session, get_session, get_session_dir,
                     get_session_files, save_file_to_session,
                     cleanup_expired_sessions)

app = FastAPI(title="AURA Analytics")

# ── Helper: get or create session from cookie ─────────────────
def get_or_create_session(request: Request):
    session_id = request.cookies.get("aura_session")
    if session_id and get_session(session_id):
        return session_id
    return create_session()

# ── Home — upload page ────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    session_id = request.cookies.get("aura_session")
    has_session = session_id and get_session(session_id)

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
            .container { text-align: center; padding: 40px; max-width: 700px; }
            h1 { color: white; font-size: 3em; margin-bottom: 10px; letter-spacing: 3px; }
            .tagline { color: #a0aec0; font-size: 1.1em; margin-bottom: 40px; }
            .upload-box {
                background: rgba(255,255,255,0.05);
                border: 2px dashed rgba(255,255,255,0.3);
                border-radius: 15px;
                padding: 40px 50px;
            }
            .upload-box h2 { color: white; margin-bottom: 10px; }
            .upload-box p { color: #a0aec0; margin-bottom: 20px; font-size:0.9em; }
            input[type=file] { color: white; margin: 15px 0; display: block; width: 100%; }
            .btn {
                display: inline-block;
                background: linear-gradient(90deg, #3498db, #2ecc71);
                color: white; border: none; padding: 14px 30px;
                border-radius: 8px; cursor: pointer; font-size: 15px;
                font-weight: bold; width: 100%; letter-spacing: 1px;
                text-decoration: none; margin-top: 10px;
            }
            .btn:hover { opacity: 0.9; }
            .btn-outline {
                display: inline-block;
                background: rgba(255,255,255,0.1);
                color: white; border: 1px solid rgba(255,255,255,0.3);
                padding: 12px 30px; border-radius: 8px;
                cursor: pointer; font-size: 15px; width: 100%;
                text-decoration: none; margin-top: 10px;
            }
            .features {
                display: grid; grid-template-columns: repeat(2, 1fr);
                gap: 15px; margin-top: 30px;
            }
            .feature {
                background: rgba(255,255,255,0.05);
                border-radius: 10px; padding: 15px; color: white; text-align:left;
            }
            .feature-icon { font-size: 1.5em; margin-bottom: 5px; }
            .feature-title { font-weight: bold; font-size:0.9em; }
            .feature-desc { color: #a0aec0; font-size: 0.8em; margin-top:3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AURA</h1>
            <p class="tagline">Your Autonomous Data Analyst</p>
            <div class="upload-box">
                <h2>Upload Your Data</h2>
                <p>Upload one file, multiple files, or a whole folder.<br>
                   AURA will organize, analyze, and find insights automatically.</p>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" name="files"
                           accept=".csv,.xlsx" multiple required>
                    <button type="submit" class="btn">
                        ⚡ Upload & Start Analysis
                    </button>
                </form>
                """ + (f'<a href="/manager" class="btn-outline">📁 Continue Previous Session</a>' if has_session else "") + """
            </div>
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">📁</div>
                    <div class="feature-title">File Manager</div>
                    <div class="feature-desc">View, edit, and manage all your files in one place</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🤖</div>
                    <div class="feature-title">AI Analyst</div>
                    <div class="feature-desc">Ask questions in plain English, get real answers</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <div class="feature-title">Auto Dashboard</div>
                    <div class="feature-desc">Charts and insights generated automatically</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🔗</div>
                    <div class="feature-title">Compare Files</div>
                    <div class="feature-desc">Compare two files or combine monthly data</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """# ── Upload files ──────────────────────────────────────────────
@app.post("/upload")
async def upload(request: Request, files: list[UploadFile] = File(...)):
    # Get or create session
    session_id = get_or_create_session(request)

    # Save each file
    saved = []
    for file in files:
        if not file.filename.endswith((".csv", ".xlsx")):
            continue
        contents = await file.read()
        save_file_to_session(session_id, file.filename, contents)
        saved.append(file.filename)

    # Redirect to file manager
    response = RedirectResponse(url="/manager", status_code=303)
    response.set_cookie("aura_session", session_id,
                        max_age=86400)  # 24 hours
    return response

# ── File Manager ──────────────────────────────────────────────
@app.get("/manager", response_class=HTMLResponse)
def manager(request: Request):
    session_id = request.cookies.get("aura_session")
    if not session_id or not get_session(session_id):
        return RedirectResponse(url="/")

    files = get_session_files(session_id)

    # Build file rows
    file_rows = ""
    file_options = ""
    for f in files:
        file_rows += f"""
        <tr>
            <td>📄 {f['name']}</td>
            <td>{f['size_str']}</td>
            <td>
                <a href="/view/{session_id}/{f['name']}" class="btn-sm btn-blue">👁 View</a>
                <a href="/analyze/{session_id}/{f['name']}" class="btn-sm btn-green">🔍 Analyze</a>
                <a href="/clean/{session_id}/{f['name']}" class="btn-sm btn-orange">🧹 Clean</a>
                <a href="/delete/{session_id}/{f['name']}" class="btn-sm btn-red"
                   onclick="return confirm('Delete {f['name']}?')">🗑 Delete</a>
            </td>
        </tr>"""
        file_options += f'<option value="{f["name"]}">{f["name"]}</option>'

    if not files:
        file_rows = """
        <tr>
            <td colspan="3" style="text-align:center;color:#888;padding:30px">
                No files uploaded yet.
                <a href="/">Upload files</a>
            </td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA — File Manager</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif;
                   background: #f0f2f5; color: #2c3e50; }}
            .header {{
                background: linear-gradient(135deg, #1a1a2e, #0f3460);
                color: white; padding: 15px 30px;
                display: flex; align-items: center;
                justify-content: space-between;
            }}
            .header h1 {{ font-size: 1.4em; letter-spacing: 2px; }}
            .header-right {{ display: flex; gap: 10px; }}
            .main {{ max-width: 1100px; margin: 30px auto; padding: 0 20px; }}
            .card {{
                background: white; border-radius: 10px; padding: 25px;
                margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            .card h2 {{
                font-size: 1.1em; margin-bottom: 15px; color: #2c3e50;
                border-bottom: 2px solid #3498db; padding-bottom: 8px;
            }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 12px; text-align: left;
                     border-bottom: 1px solid #f0f0f0; }}
            th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
            tr:hover {{ background: #fafafa; }}
            .btn-sm {{
                display: inline-block; padding: 5px 12px;
                border-radius: 5px; text-decoration: none;
                font-size: 0.82em; font-weight: 600; margin: 2px;
            }}
            .btn-blue   {{ background: #3498db; color: white; }}
            .btn-green  {{ background: #27ae60; color: white; }}
            .btn-orange {{ background: #e67e22; color: white; }}
            .btn-red    {{ background: #e74c3c; color: white; }}
            .btn-purple {{ background: #8e44ad; color: white; }}
            .btn {{
                display: inline-block; padding: 10px 20px;
                border-radius: 8px; text-decoration: none;
                font-size: 0.9em; font-weight: 600;
                border: none; cursor: pointer; margin: 5px;
            }}
            .actions-grid {{
                display: grid; grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}
            select, input[type=file] {{
                width: 100%; padding: 10px; margin: 8px 0;
                border: 1px solid #ddd; border-radius: 8px;
                font-size: 0.9em;
            }}
            .upload-inline {{
                background: #f8f9ff; border: 2px dashed #3498db;
                border-radius: 10px; padding: 20px; text-align: center;
            }}
            .header-btn {{
                background: rgba(255,255,255,0.1); color: white;
                padding: 8px 15px; border-radius: 5px;
                text-decoration: none; font-size: 0.85em;
            }}
        </style>
    </head>    <body>
        <div class="header">
            <h1>AURA Analytics</h1>
            <div class="header-right">
                <a href="/ask-all/{session_id}" class="header-btn">🤖 Ask AI About All Files</a>
                <a href="/analyze-all/{session_id}" class="header-btn">📊 Analyze All Together</a>
                <a href="/" class="header-btn">+ Upload More</a>
            </div>
        </div>

        <div class="main">
            <div class="card">
                <h2>📁 Your Files ({len(files)} files)</h2>
                <table>
                    <tr>
                        <th>File Name</th>
                        <th>Size</th>
                        <th>Actions</th>
                    </tr>
                    {file_rows}
                </table>
            </div>

            <div class="actions-grid">
                <div class="card">
                    <h2>🔗 Compare Two Files</h2>
                    <p style="color:#888;font-size:0.9em;margin-bottom:10px">
                        Select two files to compare side by side.
                    </p>
                    <form action="/compare/{session_id}" method="get">
                        <label style="font-size:0.85em">File A:</label>
                        <select name="file_a">{file_options}</select>
                        <label style="font-size:0.85em">File B:</label>
                        <select name="file_b">{file_options}</select>
                        <button type="submit" class="btn btn-blue" style="width:100%;margin-top:10px">
                            Compare Files
                        </button>
                    </form>
                </div>

                <div class="card">
                    <h2>📅 Combine Monthly Files</h2>
                    <p style="color:#888;font-size:0.9em;margin-bottom:10px">
                        Stack files with the same structure into one timeline.
                    </p>
                    <form action="/combine/{session_id}" method="get">
                        <label style="font-size:0.85em">Select files to combine:</label>
                        <select name="files" multiple size="4"
                                style="height:100px">{file_options}</select>
                        <p style="color:#888;font-size:0.8em;margin-top:5px">
                            Hold Ctrl to select multiple
                        </p>
                        <button type="submit" class="btn btn-green" style="width:100%;margin-top:10px">
                            Combine & Analyze
                        </button>
                    </form>
                </div>
            </div>

            <div class="card">
                <h2>➕ Add More Files</h2>
                <div class="upload-inline">
                    <form action="/upload" method="post" enctype="multipart/form-data">
                        <input type="file" name="files" accept=".csv,.xlsx" multiple>
                        <button type="submit" class="btn btn-blue" style="margin-top:10px">
                            Upload Files
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """# ── View file ─────────────────────────────────────────────────
@app.get("/view/{session_id}/{filename}", response_class=HTMLResponse)
def view_file(session_id: str, filename: str):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if not os.path.exists(filepath):
        return HTMLResponse("<h1>File not found</h1>")

    if filename.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    # Build table
    headers = "".join(f"<th>{c}</th>" for c in df.columns)
    rows    = ""
    for _, row in df.head(100).iterrows():
        rows += "<tr>" + "".join(f"<td>{v}</td>" for v in row.values) + "</tr>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA — {filename}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif;
                   background: #f0f2f5; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1a1a2e, #0f3460);
                      color: white; padding: 15px 25px; border-radius: 10px;
                      margin-bottom: 20px; display:flex;
                      justify-content:space-between; align-items:center; }}
            .header h1 {{ font-size:1.2em; }}
            .card {{ background: white; border-radius: 10px; padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow-x:auto; }}
            table {{ border-collapse: collapse; width:100%; font-size:0.85em; }}
            th {{ background:#1a1a2e; color:white; padding:10px 12px; text-align:left; }}
            td {{ padding:8px 12px; border-bottom:1px solid #f0f0f0; }}
            tr:hover {{ background:#f8f9fa; }}
            .btn {{ display:inline-block; padding:8px 16px; border-radius:6px;
                   text-decoration:none; font-size:0.85em; font-weight:600; }}
            .btn-blue {{ background:#3498db; color:white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📄 {filename} — {len(df):,} rows × {len(df.columns)} columns</h1>
            <a href="/manager" class="btn btn-blue">← Back to Files</a>
        </div>
        <div class="card">
            <p style="color:#888;font-size:0.85em;margin-bottom:15px">
                Showing first 100 rows
            </p>
            <table>
                <tr>{headers}</tr>
                {rows}
            </table>
        </div>
    </body>
    </html>
    """

# ── Delete file ───────────────────────────────────────────────
@app.get("/delete/{session_id}/{filename}")
def delete_file(session_id: str, filename: str):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    return RedirectResponse(url="/manager", status_code=303)# ── Compare two files ─────────────────────────────────────────
@app.get("/compare/{session_id}", response_class=HTMLResponse)
def compare_files(session_id: str, file_a: str, file_b: str):
    dir_path = get_session_dir(session_id)

    def load(fname):
        path = os.path.join(dir_path, fname)
        return pd.read_csv(path) if fname.endswith(".csv") else pd.read_excel(path)

    df_a = load(file_a)
    df_b = load(file_b)

    # Find shared columns
    shared_cols = list(set(df_a.columns) & set(df_b.columns))

    # Build comparison stats
    comparison_rows = ""
    for col in df_a.columns:
        in_b = "✅" if col in df_b.columns else "❌"
        dtype_a = str(df_a[col].dtype)
        dtype_b = str(df_b[col].dtype) if col in df_b.columns else "—"
        miss_a  = f"{df_a[col].isnull().sum()/len(df_a)*100:.1f}%"
        miss_b  = f"{df_b[col].isnull().sum()/len(df_b)*100:.1f}%" if col in df_b.columns else "—"
        comparison_rows += f"""
        <tr>
            <td>{col}</td>
            <td>{dtype_a}</td>
            <td>{miss_a}</td>
            <td>{in_b}</td>
            <td>{dtype_b}</td>
            <td>{miss_b}</td>
        </tr>"""

    # Numeric comparison for shared columns
    numeric_comparison = ""
    for col in shared_cols:
        if pd.api.types.is_numeric_dtype(df_a[col]) and pd.api.types.is_numeric_dtype(df_b[col]):
            mean_a = df_a[col].mean()
            mean_b = df_b[col].mean()
            change = ((mean_b - mean_a) / mean_a * 100) if mean_a != 0 else 0
            arrow  = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            numeric_comparison += f"""
            <tr>
                <td>{col}</td>
                <td>{mean_a:.2f}</td>
                <td>{mean_b:.2f}</td>
                <td>{arrow} {change:+.1f}%</td>
            </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA — Compare Files</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif;
                   background: #f0f2f5; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1a1a2e, #0f3460);
                      color: white; padding: 15px 25px; border-radius: 10px;
                      margin-bottom: 20px; display:flex;
                      justify-content:space-between; align-items:center; }}
            .header h1 {{ font-size:1.2em; }}
            .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
            .card {{ background:white; border-radius:10px; padding:20px;
                    box-shadow:0 2px 8px rgba(0,0,0,0.08); margin-bottom:20px; }}
            .card h2 {{ font-size:1em; border-bottom:2px solid #3498db;
                       padding-bottom:8px; margin-bottom:15px; }}
            .metric {{ text-align:center; padding:15px; }}
            .metric-value {{ font-size:1.8em; font-weight:bold; color:#2c3e50; }}
            .metric-label {{ color:#888; font-size:0.85em; }}
            table {{ width:100%; border-collapse:collapse; font-size:0.85em; }}
            th {{ background:#f8f9fa; padding:10px; text-align:left;
                 font-weight:600; color:#555; }}
            td {{ padding:10px; border-bottom:1px solid #f0f0f0; }}
            .btn {{ display:inline-block; padding:8px 16px; border-radius:6px;
                   text-decoration:none; font-size:0.85em; font-weight:600; }}
            .btn-blue {{ background:#3498db; color:white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔗 Comparing: {file_a} vs {file_b}</h1>
            <a href="/manager" class="btn btn-blue">← Back to Files</a>
        </div>

        <div class="grid">
            <div class="card">
                <h2>📄 {file_a}</h2>
                <div class="metric">
                    <div class="metric-value">{len(df_a):,}</div>
                    <div class="metric-label">Rows</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{len(df_a.columns)}</div>
                    <div class="metric-label">Columns</div>
                </div>
            </div>
            <div class="card">
                <h2>📄 {file_b}</h2>
                <div class="metric">
                    <div class="metric-value">{len(df_b):,}</div>
                    <div class="metric-label">Rows</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{len(df_b.columns)}</div>
                    <div class="metric-label">Columns</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📊 Shared Columns: {len(shared_cols)}</h2>
            <p style="color:#888;font-size:0.85em;margin-bottom:10px">
                Columns that appear in both files
            </p>
            <p>{", ".join(f'<span style="background:#eef2ff;padding:3px 8px;border-radius:20px;margin:3px;display:inline-block">{c}</span>' for c in shared_cols) if shared_cols else "No shared columns found"}</p>
        </div>        {"<div class='card'><h2>📈 Metric Comparison</h2><table><tr><th>Column</th><th>" + file_a + "</th><th>" + file_b + "</th><th>Change</th></tr>" + numeric_comparison + "</table></div>" if numeric_comparison else ""}

        <div class="card">
            <h2>🔍 Column by Column</h2>
            <table>
                <tr>
                    <th>Column</th>
                    <th>{file_a} Type</th>
                    <th>{file_a} Missing</th>
                    <th>In {file_b}?</th>
                    <th>{file_b} Type</th>
                    <th>{file_b} Missing</th>
                </tr>
                {comparison_rows}
            </table>
        </div>
    </body>
    </html>
    """

# ── Combine files ─────────────────────────────────────────────
@app.get("/combine/{session_id}", response_class=HTMLResponse)
def combine_files(session_id: str, files: list[str] = None):
    from fastapi import Query
    return RedirectResponse(f"/manager")

# ── Analyze all files together ────────────────────────────────
@app.get("/analyze-all/{session_id}", response_class=HTMLResponse)
def analyze_all(session_id: str):
    files = get_session_files(session_id)
    if not files:
        return RedirectResponse("/manager")
    # Redirect to analyze the first file for now
    # Full multi-file analysis comes next
    return RedirectResponse(f"/analyze/{session_id}/{files[0]['name']}")

# ── Single file analyze ───────────────────────────────────────
@app.get("/analyze/{session_id}/{filename}", response_class=HTMLResponse)
def analyze_file(session_id: str, filename: str):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if not os.path.exists(filepath):
        return HTMLResponse("<h1>File not found</h1>")

    from analyzer import load_file, profile_dataframe
    df = load_file(filepath)
    p  = profile_dataframe(df)

    score       = p["score"]
    score_color = "#27ae60" if score >= 80 else "#f39c12" if score >= 60 else "#e74c3c"
    score_label = "Good" if score >= 80 else "Fair" if score >= 60 else "Poor"

    findings_html = "".join(f'<div class="finding">{f}</div>' for f in p["findings"]) or "<p>✅ No issues found</p>"
    cols_html     = "".join(f'<span class="tag">{c}</span>' for c in df.columns)

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
        checkboxes_html = "<p>✅ No cleaning needed.</p>"

    charts_html = p["time_chart_div"] + p["missing_chart_div"] + p["avg_chart_div"]
    if not charts_html:
        charts_html = "<p style='color:#888;text-align:center;padding:40px'>No charts available</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA — {filename}</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {{ box-sizing:border-box; margin:0; padding:0; }}
            body {{ font-family:'Segoe UI',Arial,sans-serif; background:#f0f2f5; color:#2c3e50; }}
            .header {{ background:linear-gradient(135deg,#1a1a2e,#0f3460); color:white;
                      padding:15px 30px; display:flex; align-items:center;
                      justify-content:space-between; }}
            .header h1 {{ font-size:1.2em; letter-spacing:1px; }}
            .main {{ max-width:1200px; margin:0 auto; padding:25px 20px; }}
            .metrics {{ display:grid; grid-template-columns:repeat(4,1fr);
                       gap:15px; margin-bottom:20px; }}
            .metric {{ background:white; border-radius:10px; padding:18px;
                      text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
            .metric-value {{ font-size:1.8em; font-weight:bold; color:#2c3e50; }}
            .metric-label {{ color:#888; font-size:0.82em; margin-top:4px; }}
            .score-value {{ color:{score_color}; }}
            .tabs {{ display:flex; gap:5px; margin-bottom:20px;
                    border-bottom:2px solid #ddd; }}
            .tab {{ padding:11px 22px; cursor:pointer; border-radius:8px 8px 0 0;
                   background:#e8e8e8; border:none; font-size:0.9em;
                   font-weight:500; color:#666; }}
            .tab.active {{ background:white; color:#3498db;
                          border-bottom:2px solid white; margin-bottom:-2px; }}
            .tab-content {{ display:none; }}
            .tab-content.active {{ display:block; }}
            .card {{ background:white; border-radius:10px; padding:22px;
                    margin-bottom:18px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
            .card h2 {{ font-size:1em; margin-bottom:13px; color:#2c3e50;
                       border-bottom:2px solid #3498db; padding-bottom:7px; }}
            .finding {{ padding:9px 0; border-bottom:1px solid #f0f0f0; font-size:0.92em; }}
            .tag {{ background:#eef2ff; color:#3498db; padding:3px 9px; margin:3px;
                   border-radius:20px; display:inline-block; font-size:0.82em; }}
            table {{ width:100%; border-collapse:collapse; }}
            th,td {{ padding:9px 11px; text-align:left;
                    border-bottom:1px solid #f0f0f0; font-size:0.87em; }}
            th {{ background:#f8f9fa; font-weight:600; color:#555; }}
            .charts-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
            .chart-box {{ background:white; border-radius:10px; padding:18px;
                         box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
            .chart-box h3 {{ font-size:0.9em; color:#555; margin-bottom:13px; }}
            .check-item {{ padding:11px 0; border-bottom:1px solid #f0f0f0; }}
            .check-item label {{ display:flex; align-items:center; gap:11px;
                                cursor:pointer; font-size:0.92em; }}
            .check-item input {{ width:17px; height:17px; cursor:pointer; }}
            .btn {{ display:inline-block; padding:11px 22px; border-radius:8px;
                   border:none; cursor:pointer; font-size:0.9em; font-weight:600;
                   text-decoration:none; margin:4px; }}
            .btn-green  {{ background:#27ae60; color:white; }}
            .btn-blue   {{ background:#3498db; color:white; }}
            .btn-gray   {{ background:#95a5a6; color:white; }}
            input[type=text] {{ width:100%; padding:11px; border:1px solid #ddd;
                               border-radius:8px; font-size:0.95em; margin-bottom:10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📄 {filename}</h1>
            <a href="/manager" class="btn btn-gray" style="font-size:0.82em">← File Manager</a>
        </div>

        <div class="main">
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{p['row_count']:,}</div>
                    <div class="metric-label">Total Rows</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{p['col_count']}</div>
                    <div class="metric-label">Columns</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{p['duplicate_rows']:,}</div>
                    <div class="metric-label">Duplicates</div>
                </div>
                <div class="metric">
                    <div class="metric-value score-value">{score}/100</div>
                    <div class="metric-label">Quality Score</div>
                </div>
            </div>

            <div class="tabs">
                <button class="tab active" onclick="showTab('overview',event)">📋 Overview</button>
                <button class="tab" onclick="showTab('clean',event)">🧹 Clean</button>
                <button class="tab" onclick="showTab('dashboard',event)">📊 Dashboard</button>
                <button class="tab" onclick="showTab('ai',event)">🤖 AI Insights</button>
            </div>

            <div id="overview" class="tab-content active">
                <div class="card">
                    <h2>Columns ({p['col_count']})</h2>
                    {cols_html}
                </div>
                <div class="card">
                    <h2>Quality Findings</h2>
                    {findings_html}
                </div>
                {"<div class='card'><h2>Numeric Statistics</h2><table><tr><th>Column</th><th>Mean</th><th>Median</th><th>Min</th><th>Max</th><th>Missing</th></tr>" + p['stats_rows'] + "</table></div>" if p['stats_rows'] else ""}
            </div>

            <div id="clean" class="tab-content">
                <div class="card">
                    <h2>Choose What to Fix</h2>
                    <p style="color:#888;margin-bottom:13px;font-size:0.88em">
                        Only selected fixes will be applied to your download.
                    </p>
                    <form action="/download-clean/{session_id}/{filename}" method="post">
                        {checkboxes_html}
                        <br>
                        <button type="submit" class="btn btn-green">
                            ⬇ Apply Fixes &amp; Download
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
                                padding:18px;border-radius:0 10px 10px 0;line-height:1.7">
                        <ul style="padding-left:20px;list-style:none">
                            {p['ai_html']}
                        </ul>
                    </div>
                </div>
                <div class="card">
                    <h2>Ask the AI Analyst</h2>
                    <form action="/ask-file/{session_id}/{filename}" method="post">
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
            {p['time_chart_js']}
            {p['missing_chart_js']}
            {p['avg_chart_js']}
        }}
        </script>
    </body>
    </html>
    """

# ── Placeholder for clean ─────────────────────────────────────
@app.get("/clean/{session_id}/{filename}", response_class=HTMLResponse)
def clean_file(session_id: str, filename: str):
    return HTMLResponse(f"<h1>Clean {filename} coming next</h1><a href='/manager'>Back</a>")

# ── Ask AI about all files ────────────────────────────────────
@app.get("/ask-all/{session_id}", response_class=HTMLResponse)
def ask_all(session_id: str):
    return HTMLResponse("<h1>Ask AI coming next</h1><a href='/manager'>Back</a>")
# ── Download cleaned file ─────────────────────────────────────
@app.post("/download-clean/{session_id}/{filename}")
async def download_clean(session_id: str, filename: str,
                         fixes: list[str] = Form(default=[])):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if not os.path.exists(filepath):
        return HTMLResponse("<h1>File not found</h1>")

    from analyzer import load_file
    df      = load_file(filepath)
    changes = []

    for fix in fixes:
        if fix == "remove_duplicates":
            before = len(df)
            df     = df.drop_duplicates()
            changes.append(f"Removed {before-len(df)} duplicates")
        elif fix.startswith("fill_median_"):
            col = fix.replace("fill_median_", "")
            if col in df.columns:
                val = df[col].median()
                df[col] = df[col].fillna(val)
                changes.append(f"Filled {col} with median")
        elif fix.startswith("fill_zero_"):
            col = fix.replace("fill_zero_", "")
            if col in df.columns:
                df[col] = df[col].fillna(0)
        elif fix.startswith("fill_mode_"):
            col = fix.replace("fill_mode_", "")
            if col in df.columns:
                mode = df[col].mode()
# ── Ask AI about specific file ────────────────────────────────
@app.post("/ask-file/{session_id}/{filename}", response_class=HTMLResponse)
async def ask_file(session_id: str, filename: str,
                   question: str = Form(...)):
    filepath = os.path.join(get_session_dir(session_id), filename)
    if not os.path.exists(filepath):
        return HTMLResponse("<h1>File not found</h1>")

    from analyzer import load_file
    from analytics.ai_analyst import answer_question

    df           = load_file(filepath)
    row_count    = df.shape[0]
    col_count    = df.shape[1]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    findings = []
    for col in df.columns:
        pct = round(df[col].isnull().sum() / row_count * 100, 2)
        if pct > 0:
            findings.append(f"{col}: {pct}% missing")

    numeric_stats = ""
    for col in numeric_cols[:5]:
        numeric_stats += f"{col}: mean={df[col].mean():.2f}, min={df[col].min():.2f}, max={df[col].max():.2f}\n"

    date_col = None
    for col in df.columns:
        if any(kw in col.lower() for kw in ["date","time","month","year"]):
            date_col = col
            break

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
            answer_html += f"<h3 style='margin:15px 0 8px'>{line.replace('**','')}</h3>"
        else:
            answer_html += f"<p style='margin-bottom:8px'>{line}</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA — AI Answer</title>
        <style>
            body {{ font-family:'Segoe UI',Arial,sans-serif; background:#f0f2f5;
                   max-width:800px; margin:40px auto; padding:20px; }}
            .card {{ background:white; border-radius:10px; padding:25px;
                    margin:20px 0; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
            h1 {{ color:#2c3e50; margin-bottom:20px; }}
            h2 {{ color:#34495e; border-bottom:2px solid #8e44ad;
                 padding-bottom:8px; margin-bottom:15px; }}
            .question {{ background:#f0f2f5; padding:15px; border-radius:8px;
                        margin-bottom:20px; font-style:italic; color:#555; }}
            .answer {{ background:#f8f9ff; border-left:4px solid #8e44ad;
                      padding:20px; border-radius:0 10px 10px 0; line-height:1.7; }}
            .btn {{ display:inline-block; padding:10px 20px; border-radius:8px;
                   text-decoration:none; font-size:0.9em; font-weight:600; margin:5px; }}
            .btn-blue {{ background:#3498db; color:white; }}
            .btn-gray {{ background:#95a5a6; color:white; }}
        </style>
    </head>
    <body>
        <h1>🤖 AURA AI Analyst</h1>
        <div class="card">
            <h2>Your Question</h2>
            <div class="question">"{question}"</div>
            <h2>AURA's Answer</h2>
            <div class="answer">
                <ul style="padding-left:20px;list-style:none">
                    {answer_html}
                </ul>
            </div>
        </div>
        <a href="javascript:history.back()" class="btn btn-gray">← Back</a>
        <a href="/manager" class="btn btn-blue">📁 File Manager</a>
    </body>
    </html>
    """
                if len(mode) > 0:
                    df[col] = df[col].fillna(mode[0])
        elif fix.startswith("fix_date_"):
            col = fix.replace("fix_date_", "")
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    output     = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    clean_name = filename.replace(".csv","_cleaned.csv").replace(".xlsx","_cleaned.csv")

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={clean_name}"}
    )