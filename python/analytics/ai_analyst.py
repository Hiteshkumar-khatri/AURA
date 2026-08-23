import requests
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

# ── Call OpenRouter ───────────────────────────────────────────
def ask_ai(system_prompt, user_prompt):
    if not OPENROUTER_API_KEY:
        return "AI not configured — add OPENROUTER_API_KEY to .env"

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                "max_tokens": 800,
            },
            timeout=30
        )
        data = response.json()

        if "error" in data:
            return f"AI error: {data['error'].get('message', 'Unknown error')}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"AI unavailable: {str(e)}"

# ── Analyze dataset and generate insights ─────────────────────
def analyze_dataset(filename, row_count, col_count,
                    duplicate_rows, score, findings,
                    numeric_stats, date_col, scenario):

    system_prompt = """You are AURA, a professional data analyst AI.
You analyze datasets and provide clear, honest, actionable insights.

Rules:
- Only use the data provided to you. Never invent numbers.
- Clearly separate observations from recommendations.
- Be concise — maximum 5 bullet points per section.
- Use plain English, not technical jargon.
- If data is insufficient to draw conclusions, say so honestly.
- Never claim causation without evidence."""

    user_prompt = f"""Analyze this dataset and provide insights:

FILE: {filename}
SCENARIO: {scenario}
ROWS: {row_count:,}
COLUMNS: {col_count}
DUPLICATE ROWS: {duplicate_rows:,}
QUALITY SCORE: {score}/100

QUALITY FINDINGS:
{chr(10).join(findings) if findings else 'No issues found'}

NUMERIC STATISTICS:
{numeric_stats}

DATE COLUMN DETECTED: {date_col if date_col else 'None'}

Provide:
1. DATASET SUMMARY (2-3 sentences about what this data appears to be)
2. KEY CONCERNS (top issues found, if any)
3. RECOMMENDATIONS (what the user should do next)
4. WHAT ANALYSIS IS POSSIBLE (what insights can be extracted from this data)

Be specific and actionable."""

    return ask_ai(system_prompt, user_prompt)

# ── Answer a specific user question ──────────────────────────
def answer_question(question, filename, row_count,
                    col_count, findings, numeric_stats,
                    columns, date_col):

    system_prompt = """You are AURA, a professional data analyst AI.
A user has uploaded a dataset and is asking you a question about it.

Rules:
- Only use the provided data context. Never invent numbers.
- Be direct and specific.
- If you cannot answer from the available data, say what additional data would be needed.
- Distinguish between what the data shows vs what might explain it."""

    user_prompt = f"""Dataset context:
FILE: {filename}
ROWS: {row_count:,}
COLUMNS: {', '.join(columns)}
DATE COLUMN: {date_col if date_col else 'None detected'}

QUALITY FINDINGS:
{chr(10).join(findings) if findings else 'No issues'}

NUMERIC STATISTICS:
{numeric_stats}

USER QUESTION: {question}

Answer the question based on the available data context."""

    return ask_ai(system_prompt, user_prompt)