import requests
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

# ── Call OpenRouter ───────────────────────────────────────────
def call_ai(messages, max_tokens=800):
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
                "messages": messages,
                "max_tokens": max_tokens,
            },
            timeout=30
        )
        data = response.json()
        if "error" in data:
            return f"AI error: {data['error'].get('message', 'Unknown error')}"
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI unavailable: {str(e)}"

# ── Analyze dataset ───────────────────────────────────────────
def analyze_dataset(filename, row_count, col_count,
                    duplicate_rows, score, findings,
                    numeric_stats, date_col, scenario):

    messages = [
        {
            "role": "system",
            "content": """You are AURA, a professional data analyst AI.
Analyze datasets and provide clear, honest, actionable insights.
Rules:
- Only use the data provided. Never invent numbers.
- Separate observations from recommendations.
- Maximum 5 bullet points per section.
- Use plain English, not jargon.
- If data is insufficient, say so honestly.
- Never claim causation without evidence."""
        },
        {
            "role": "user",
            "content": f"""Analyze this dataset:

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

DATE COLUMN: {date_col if date_col else 'None'}

Provide:
1. DATASET SUMMARY (2-3 sentences)
2. KEY CONCERNS (top issues found)
3. RECOMMENDATIONS (what to do next)
4. WHAT ANALYSIS IS POSSIBLE"""
        }
    ]
    return call_ai(messages)

# ── Answer question with tool results ────────────────────────
def answer_with_tools(question, filename, columns,
                      tool_results, conversation_history=None):

    system_msg = {
        "role": "system",
        "content": """You are AURA, a professional data analyst AI.
You have been given real calculated results from analytical tools.
Your job is to explain these results clearly and honestly.

CRITICAL RULES:
- Only use the tool results provided. Never invent numbers.
- Every specific number in your answer must come from the tool results.
- Distinguish between what the data SHOWS vs what might EXPLAIN it.
- If a question cannot be answered from available data, say so clearly.
- Be concise and specific. No filler words.
- End with one concrete recommendation based on the evidence."""
    }

    # Build tool results summary
    tool_summary = ""
    for tool_name, result in tool_results.items():
        tool_summary += f"\n--- {tool_name} ---\n{json.dumps(result, indent=2)}\n"

    user_msg = {
        "role": "user",
        "content": f"""Dataset: {filename}
Columns: {', '.join(columns)}

REAL CALCULATED RESULTS FROM ANALYTICAL TOOLS:
{tool_summary}

USER QUESTION: {question}

Answer the question using ONLY the tool results above.
Be specific with numbers. Show your reasoning."""
    }

    messages = [system_msg]

    # Add conversation history for follow-up questions
    if conversation_history:
        messages.extend(conversation_history)

    messages.append(user_msg)
    return call_ai(messages, max_tokens=1000)

# ── Plan which tools to run for a question ────────────────────
def plan_analysis(question, overview):
    messages = [
        {
            "role": "system",
            "content": """You are AURA's analysis planner.
Given a user question and dataset overview, decide which analytical tools to run.

Available tools:
- get_column_stats(column) — statistics for one column
- group_by(metric, group) — breakdown by category
- compare_periods(metric, period1, period2) — compare two time periods
- monthly_trend(metric) — trend over time
- detect_anomalies(metric) — find unusual values
- calculate_correlation(col1, col2) — relationship between columns
- top_contributors(metric, group) — what drives a metric
- get_available_periods() — what time periods exist

Respond with a JSON array of tool calls. Example:
[
  {"tool": "monthly_trend", "params": {"metric": "Sales_Amount"}},
  {"tool": "group_by", "params": {"metric": "Sales_Amount", "group": "Region"}}
]

Only include tools that are relevant to the question.
Maximum 4 tool calls. Return ONLY the JSON array, nothing else."""
        },
        {
            "role": "user",
            "content": f"""Question: {question}

Dataset overview:
{json.dumps(overview, indent=2)}

Which tools should I run to answer this question?"""
        }
    ]

    response = call_ai(messages, max_tokens=300)

    # Parse JSON response
    try:
        # Clean response — remove markdown if present
        clean = response.strip()
        if clean.startswith("`"):
            clean = clean.split("`")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except:
        # Fallback — run basic tools
        numeric_cols = overview.get("numeric_cols", [])
        if numeric_cols:
            return [{"tool": "get_column_stats", "params": {"column": numeric_cols[0]}}]
        return []
# ── Answer a specific question about a dataset ────────────────
def answer_question(question, filename, row_count, col_count,
                    findings, numeric_stats, columns, date_col):
    messages = [
        {
            "role": "system",
            "content": """You are AURA, a professional data analyst AI.
Answer the user's question about their dataset clearly and honestly.
Rules:
- Only use the data provided. Never invent numbers.
- Separate observations from recommendations.
- Maximum 5 bullet points per section.
- Use plain English, not jargon.
- If data is insufficient to answer, say so honestly.
- Never claim causation without evidence."""
        },
        {
            "role": "user",
            "content": f"""Answer this question about the dataset:

QUESTION: {question}

FILE: {filename}
ROWS: {row_count:,}
COLUMNS: {col_count}
COLUMNS LIST: {', '.join(columns)}
DATE COLUMN: {date_col if date_col else 'None'}

QUALITY FINDINGS:
{chr(10).join(findings) if findings else 'No issues found'}

NUMERIC STATISTICS:
{numeric_stats}

Provide:
1. DIRECT ANSWER (answer the question using the data)
2. KEY EVIDENCE (specific numbers that support the answer)
3. CAVEATS (limits / what the data cannot tell us)
4. RECOMMENDED NEXT STEP"""
        }
    ]
    return call_ai(messages)
# ── Answer a specific question about a dataset ────────────────
def answer_question(question, filename, row_count, col_count,
                    findings, numeric_stats, columns, date_col):
    messages = [
        {
            "role": "system",
            "content": """You are AURA, a professional data analyst AI.
Answer the user's question about their dataset clearly and honestly.
Rules:
- Only use the data provided. Never invent numbers.
- Separate observations from recommendations.
- Maximum 5 bullet points per section.
- Use plain English, not jargon.
- If data is insufficient to answer, say so honestly.
- Never claim causation without evidence."""
        },
        {
            "role": "user",
            "content": f"""Answer this question about the dataset:

QUESTION: {question}

FILE: {filename}
ROWS: {row_count:,}
COLUMNS: {col_count}
COLUMNS LIST: {', '.join(columns)}
DATE COLUMN: {date_col if date_col else 'None'}

QUALITY FINDINGS:
{chr(10).join(findings) if findings else 'No issues found'}

NUMERIC STATISTICS:
{numeric}

Provide:
1. DIRECT ANSWER (answer the question using the data)
2. KEY EVIDENCE (specific numbers that support the answer)
3. CAVEATS (limits / what the data cannot tell us)
4. RECOMMENDED NEXT STEP"""
        }
    ]
    return call_ai(messages)
