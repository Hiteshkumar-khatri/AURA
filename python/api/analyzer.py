import pandas as pd
import io
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from analytics.ai_analyst import analyze_dataset

def load_file(filepath):
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)
    else:
        return pd.read_excel(filepath)

def profile_dataframe(df):
    row_count      = df.shape[0]
    col_count      = df.shape[1]
    duplicate_rows = int(df.duplicated().sum())
    numeric_cols   = df.select_dtypes(include="number").columns.tolist()
    text_cols      = df.select_dtypes(include="object").columns.tolist()

    findings = []
    score    = 100.0
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
        clean_opts.append(("remove_duplicates",
                           f"Remove {duplicate_rows:,} duplicate rows"))

    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            clean_opts.append((f"fill_median_{col}",
                               f"Fill missing in <b>{col}</b> with median ({df[col].median():.2f})"))
            clean_opts.append((f"fill_zero_{col}",
                               f"Fill missing in <b>{col}</b> with zero"))

    for col in text_cols:
        if df[col].isnull().sum() > 0:
            mode = df[col].mode()
            if len(mode) > 0:
                clean_opts.append((f"fill_mode_{col}",
                                   f"Fill missing in <b>{col}</b> with '{mode[0]}'"))

    date_col = None
    df_c     = df.copy()
    for col in df_c.columns:
        if any(kw in col.lower() for kw in ["date","time","month","year"]):
            if df_c[col].dtype == object:
                clean_opts.append((f"fix_date_{col}",
                                   f"Convert <b>{col}</b> to proper date format"))
            try:
                df_c[col] = pd.to_datetime(df_c[col], errors="coerce")
                if df_c[col].notna().sum() > 0:
                    date_col = col
                    break
            except:
                pass

    score = max(round(score, 1), 0)

    # Stats
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
# Charts
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

    missing_labels    = []
    missing_values_list = []
    for col in df.columns:
        pct = round(df[col].isnull().sum() / row_count * 100, 2)
        if pct > 0:
            missing_labels.append(col)
            missing_values_list.append(pct)

    missing_chart_div = ""
    missing_chart_js  = ""
    if missing_labels:
        missing_chart_div = "<div class='chart-box'><h3>Missing Values (%)</h3><canvas id='missingChart'></canvas></div>"
        missing_chart_js  = f"""
        new Chart(document.getElementById('missingChart'), {{
            type: 'bar',
            data: {{
                labels: {missing_labels},
                datasets: [{{ label: 'Missing %', data: {missing_values_list}, backgroundColor: '#e74c3c' }}]
            }},
            options: {{ responsive: true }}
        }});"""

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
# AI
    ai_insights = analyze_dataset(
        filename       = "dataset",
        row_count      = row_count,
        col_count      = col_count,
        duplicate_rows = duplicate_rows,
        score          = score,
        findings       = [f.replace('<b>','').replace('</b>','') for f in findings],
        numeric_stats  = numeric_stats_txt,
        date_col       = date_col,
        scenario       = "single"
    )

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

    return {
        "row_count":      row_count,
        "col_count":      col_count,
        "duplicate_rows": duplicate_rows,
        "numeric_cols":   numeric_cols,
        "findings":       findings,
        "score":          score,
        "clean_opts":     clean_opts,
        "stats_rows":     stats_rows,
        "date_col":       date_col,
        "time_chart_div": time_chart_div,
        "time_chart_js":  time_chart_js,
        "missing_chart_div": missing_chart_div,
        "missing_chart_js":  missing_chart_js,
        "avg_chart_div":  avg_chart_div,
        "avg_chart_js":   avg_chart_js,
        "ai_html":        ai_html,
    }