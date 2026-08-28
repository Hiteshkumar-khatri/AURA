def sidebar_layout(content, active_page="dashboard", session_id=""):
    nav_items = [
        ("dashboard",   "📊", "Dashboard",        f"/dashboard/{session_id}"),
        ("chat",        "💬", "Chat with AURA",   f"/chat/{session_id}"),
        ("files",       "📁", "My Files",          f"/manager"),
        ("quality",     "🔍", "Data Quality",      f"/quality/{session_id}"),
        ("kpis",        "📈", "KPIs & Metrics",    f"/kpis/{session_id}"),
        ("anomalies",   "🚨", "Anomaly Detection", f"/anomalies/{session_id}"),
        ("segments",    "👥", "Segmentation",      f"/segments/{session_id}"),
        ("clean",       "🧹", "Data Cleaning",     f"/clean-hub/{session_id}"),
        ("reports",     "📑", "Reports",           f"/reports/{session_id}"),
    ]

    nav_html = ""
    for page_id, icon, label, href in nav_items:
        active_class = "active" if page_id == active_page else ""
        nav_html += f"""
        <a href="{href}" class="nav-item {active_class}">
            <span class="nav-icon">{icon}</span>
            <span class="nav-label">{label}</span>
        </a>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AURA Analytics</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {{ box-sizing:border-box; margin:0; padding:0; }}
            body {{
                font-family:'Segoe UI',Arial,sans-serif;
                background:#0d1117;
                color:#e6edf3;
                display:flex;
                min-height:100vh;
            }}

            /* ── Sidebar ── */
            .sidebar {{
                width:220px;
                background:#161b22;
                border-right:1px solid #30363d;
                display:flex;
                flex-direction:column;
                position:fixed;
                height:100vh;
                z-index:100;
            }}
            .sidebar-logo {{
                padding:20px;
                border-bottom:1px solid #30363d;
            }}
            .sidebar-logo h1 {{
                font-size:1.4em;
                letter-spacing:3px;
                background:linear-gradient(90deg,#3498db,#2ecc71);
                -webkit-background-clip:text;
                -webkit-text-fill-color:transparent;
                font-weight:900;
            }}
            .sidebar-logo p {{
                color:#8b949e;
                font-size:0.72em;
                margin-top:3px;
            }}
            .nav-section {{
                padding:15px 10px 5px;
                color:#8b949e;
                font-size:0.7em;
                letter-spacing:1px;
                text-transform:uppercase;
            }}
            .nav-item {{
                display:flex;
                align-items:center;
                gap:10px;
                padding:10px 15px;
                margin:2px 8px;
                border-radius:8px;
                text-decoration:none;
                color:#8b949e;
                font-size:0.88em;
                transition:all 0.2s;
            }}
            .nav-item:hover {{
                background:#21262d;
                color:#e6edf3;
            }}
            .nav-item.active {{
                background:linear-gradient(90deg,rgba(52,152,219,0.15),rgba(46,204,113,0.1));
                color:#3498db;
                border-left:3px solid #3498db;
            }}
            .nav-icon {{ font-size:1em; width:20px; text-align:center; }}
            .nav-label {{ font-weight:500; }}
.sidebar-bottom {{
                margin-top:auto;
                padding:15px;
                border-top:1px solid #30363d;
            }}
            .help-link {{
                display:flex;
                align-items:center;
                gap:8px;
                color:#8b949e;
                font-size:0.82em;
                text-decoration:none;
            }}
            .help-link:hover {{ color:#e6edf3; }}

            /* ── Main content ── */
            .main-content {{
                margin-left:220px;
                flex:1;
                display:flex;
                flex-direction:column;
                min-height:100vh;
            }}

            /* ── Top bar ── */
            .topbar {{
                background:#161b22;
                border-bottom:1px solid #30363d;
                padding:12px 25px;
                display:flex;
                align-items:center;
                justify-content:space-between;
                position:sticky;
                top:0;
                z-index:50;
            }}
            .topbar-left h2 {{
                font-size:1.1em;
                color:#e6edf3;
                font-weight:600;
            }}
            .topbar-left p {{
                color:#8b949e;
                font-size:0.8em;
                margin-top:2px;
            }}
            .topbar-right {{
                display:flex;
                align-items:center;
                gap:10px;
            }}
            .topbar-btn {{
                background:#21262d;
                color:#e6edf3;
                border:1px solid #30363d;
                padding:7px 14px;
                border-radius:6px;
                text-decoration:none;
                font-size:0.82em;
                cursor:pointer;
            }}
            .topbar-btn:hover {{ background:#30363d; }}
            .topbar-btn.primary {{
                background:linear-gradient(90deg,#3498db,#2ecc71);
                border:none;
                color:white;
                font-weight:600;
            }}

            /* ── Page content ── */
            .page-content {{
                padding:25px;
                flex:1;
            }}

            /* ── Metric cards ── */
            .metrics-grid {{
                display:grid;
                grid-template-columns:repeat(5,1fr);
                gap:15px;
                margin-bottom:22px;
            }}
            .metric-card {{
                background:#161b22;
                border:1px solid #30363d;
                border-radius:10px;
                padding:18px;
            }}
            .metric-label {{
                color:#8b949e;
                font-size:0.75em;
                margin-bottom:8px;
                display:flex;
                align-items:center;
                gap:6px;
            }}
            .metric-value {{
                font-size:1.6em;
                font-weight:700;
                color:#e6edf3;
            }}
            .metric-change {{
                font-size:0.75em;
                margin-top:5px;
            }}
            .metric-change.up {{ color:#2ecc71; }}
            .metric-change.down {{ color:#e74c3c; }}
            .metric-change.neutral {{ color:#8b949e; }}

            /* ── Chart cards ── */
            .charts-grid {{
                display:grid;
                grid-template-columns:2fr 1fr;
                gap:18px;
                margin-bottom:22px;
            }}
            .charts-grid-3 {{
                display:grid;
                grid-template-columns:1fr 1fr 1fr;
                gap:18px;
                margin-bottom:22px;
            }}
            .chart-card {{
                background:#161b22;
                border:1px solid #30363d;
                border-radius:10px;
                padding:20px;
            }}
            .chart-card h3 {{
                font-size:0.9em;
                color:#e6edf3;
                margin-bottom:15px;
                font-weight:600;
            }}
/* ── Tables ── */
            .table-card {{
                background:#161b22;
                border:1px solid #30363d;
                border-radius:10px;
                padding:20px;
                margin-bottom:18px;
            }}
            .table-card h3 {{
                font-size:0.9em;
                color:#e6edf3;
                margin-bottom:15px;
                font-weight:600;
            }}
            table {{ width:100%; border-collapse:collapse; }}
            th {{
                background:#0d1117;
                padding:10px 12px;
                text-align:left;
                font-size:0.78em;
                color:#8b949e;
                font-weight:600;
                border-bottom:1px solid #30363d;
            }}
            td {{
                padding:10px 12px;
                border-bottom:1px solid #21262d;
                font-size:0.85em;
                color:#e6edf3;
            }}
            tr:hover td {{ background:#21262d; }}

            /* ── Findings ── */
            .finding {{
                padding:10px 0;
                border-bottom:1px solid #21262d;
                font-size:0.87em;
            }}
            .tag {{
                background:#21262d;
                color:#3498db;
                padding:3px 9px;
                margin:3px;
                border-radius:20px;
                display:inline-block;
                font-size:0.8em;
                border:1px solid #30363d;
            }}

            /* ── Score ring ── */
            .score-ring {{
                width:90px;
                height:90px;
                border-radius:50%;
                display:flex;
                align-items:center;
                justify-content:center;
                flex-direction:column;
                font-weight:700;
                font-size:1.2em;
            }}

            /* ── Buttons ── */
            .btn {{
                display:inline-block;
                padding:8px 18px;
                border-radius:6px;
                border:none;
                cursor:pointer;
                font-size:0.85em;
                font-weight:600;
                text-decoration:none;
                margin:3px;
            }}
            .btn-primary {{
                background:linear-gradient(90deg,#3498db,#2ecc71);
                color:white;
            }}
            .btn-secondary {{
                background:#21262d;
                color:#e6edf3;
                border:1px solid #30363d;
            }}
            .btn-danger {{
                background:#e74c3c;
                color:white;
            }}
            .btn-warning {{
                background:#e67e22;
                color:white;
            }}
            .btn:hover {{ opacity:0.85; }}

            /* ── Form elements ── */
            input[type=text], input[type=file], select, textarea {{
                background:#21262d;
                border:1px solid #30363d;
                color:#e6edf3;
                padding:10px 14px;
                border-radius:6px;
                font-size:0.88em;
                width:100%;
                margin:6px 0;
            }}
            input[type=text]:focus, select:focus {{
                outline:none;
                border-color:#3498db;
            }}
            input[type=file] {{ color:#8b949e; }}

            /* ── Chat bar ── */
            .chat-bar {{
                background:#161b22;
                border-top:1px solid #30363d;
                padding:15px 25px;
                display:flex;
                gap:12px;
                align-items:center;
            }}
            .chat-bar input {{
                flex:1;
                background:#21262d;
                border:1px solid #30363d;
                color:#e6edf3;
                padding:11px 16px;
                border-radius:25px;
                font-size:0.9em;
                margin:0;
            }}
            .chat-bar input:focus {{
                outline:none;
                border-color:#3498db;
            }}
            .chat-send {{
                background:linear-gradient(90deg,#3498db,#2ecc71);
                border:none;
                color:white;
                padding:11px 20px;
                border-radius:25px;
                cursor:pointer;
                font-weight:600;
                font-size:0.9em;
            }}

            /* ── Badges ── */
            .badge {{
                display:inline-block;
                padding:2px 8px;
                border-radius:20px;
                font-size:0.75em;
                font-weight:600;
            }}
            .badge-green  {{ background:rgba(46,204,113,0.15); color:#2ecc71; }}
            .badge-red    {{ background:rgba(231,76,60,0.15);  color:#e74c3c; }}
            .badge-yellow {{ background:rgba(241,196,15,0.15); color:#f1c40f; }}
            .badge-blue   {{ background:rgba(52,152,219,0.15); color:#3498db; }}

            /* ── Upload area ── */
            .upload-zone {{
                background:#0d1117;
                border:2px dashed #30363d;
                border-radius:12px;
                padding:40px;
                text-align:center;
                transition:border-color 0.2s;
            }}
            .upload-zone:hover {{ border-color:#3498db; }}
            .upload-zone h3 {{ color:#e6edf3; margin-bottom:8px; }}
            .upload-zone p  {{ color:#8b949e; font-size:0.88em; margin-bottom:15px; }}

            /* ── Check items ── */
            .check-item {{
                padding:11px 0;
                border-bottom:1px solid #21262d;
            }}
            .check-item label {{
                display:flex; align-items:center;
                gap:11px; cursor:pointer; font-size:0.88em; color:#e6edf3;
            }}
            .check-item input[type=checkbox] {{
                width:17px; height:17px; cursor:pointer; margin:0; padding:0;
                background:#21262d; border:1px solid #30363d;
            }}

            /* ── AI box ── */
            .ai-response {{
                background:#0d1117;
                border-left:3px solid #8e44ad;
                padding:18px;
                border-radius:0 8px 8px 0;
                line-height:1.7;
                font-size:0.9em;
            }}

            /* ── Tabs ── */
            .tabs {{
                display:flex;
                gap:4px;
                margin-bottom:18px;
                border-bottom:1px solid #30363d;
            }}
            .tab {{
                padding:9px 18px;
                cursor:pointer;
                border-radius:6px 6px 0 0;
                background:transparent;
                border:none;
                font-size:0.85em;
                font-weight:500;
                color:#8b949e;
            }}
            .tab.active {{
                background:#161b22;
                color:#3498db;
                border-bottom:2px solid #3498db;
                margin-bottom:-1px;
            }}
            .tab-content {{ display:none; }}
            .tab-content.active {{ display:block; }}

            /* ── Scrollbar ── */
            ::-webkit-scrollbar {{ width:6px; }}
            ::-webkit-scrollbar-track {{ background:#0d1117; }}
            ::-webkit-scrollbar-thumb {{ background:#30363d; border-radius:3px; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-logo">
                <h1>AURA</h1>
                <p>AI Data Analyst</p>
            </div>

            <div class="nav-section">Analyze</div>
            {nav_html}

            <div class="sidebar-bottom">
                <a href="/" class="help-link">
                    📤 Upload New Files
                </a>
            </div>
        </div>

        <div class="main-content">
            {content}
        </div>
    </body>
    </html>
    """