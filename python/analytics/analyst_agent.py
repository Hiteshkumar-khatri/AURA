import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from analytics.tools import AuraTools
from analytics.ai_analyst import plan_analysis, answer_with_tools, analyze_dataset

class AnalystAgent:

    def __init__(self, df, filename):
        self.tools    = AuraTools(df, filename)
        self.filename = filename
        self.df       = df
        self.history  = []  # conversation history
        self.overview = self.tools.get_overview()

    def run_tool(self, tool_name, params):
        tool_map = {
            "get_column_stats":      self.tools.get_column_stats,
            "group_by":              self.tools.group_by,
            "compare_periods":       self.tools.compare_periods,
            "monthly_trend":         self.tools.monthly_trend,
            "detect_anomalies":      self.tools.detect_anomalies,
            "calculate_correlation": self.tools.calculate_correlation,
            "top_contributors":      self.tools.top_contributors,
            "get_available_periods": self.tools.get_available_periods,
        }
        if tool_name not in tool_map:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return tool_map[tool_name](**params)
        except Exception as e:
            return {"error": str(e)}

    def answer(self, question):
        # Step 1 — AI plans which tools to run
        plan = plan_analysis(question, self.overview)

        # Step 2 — Run the tools and collect real results
        tool_results = {}
        for step in plan:
            tool_name = step.get("tool")
            params    = step.get("params", {})
            result    = self.run_tool(tool_name, params)
            tool_results[f"{tool_name}({params})"] = result

        # Step 3 — AI explains the real results
        answer = answer_with_tools(
            question         = question,
            filename         = self.filename,
            columns          = list(self.df.columns),
            tool_results     = tool_results,
            conversation_history = self.history if self.history else None
        )

        # Step 4 — Save to conversation history
        self.history.append({"role": "user",      "content": question})
        self.history.append({"role": "assistant",  "content": answer})

        # Keep history manageable
        if len(self.history) > 10:
            self.history = self.history[-10:]

        return {
            "question":     question,
            "plan":         plan,
            "tool_results": tool_results,
            "answer":       answer,
            "audit_trail":  self.tools.get_audit_trail()
        }

    def get_initial_analysis(self):
        numeric_cols  = self.overview.get("numeric_cols", [])
        findings      = []
        score         = 100.0
        row_count     = self.overview["rows"]

        for col in self.df.columns:
            pct = round(self.df[col].isnull().sum() / row_count * 100, 2)
            if pct > 0:
                findings.append(f"{col}: {pct}% missing")
                score -= (20 if pct > 50 else 10 if pct > 20 else 5 if pct > 5 else 1)

        numeric_stats = ""
        for col in numeric_cols[:5]:
            numeric_stats += f"{col}: mean={self.df[col].mean():.2f}, min={self.df[col].min():.2f}, max={self.df[col].max():.2f}\n"

        return analyze_dataset(
            filename       = self.filename,
            row_count      = row_count,
            col_count      = self.overview["columns"],
            duplicate_rows = self.overview["duplicates"],
            score          = max(round(score, 1), 0),
            findings       = findings,
            numeric_stats  = numeric_stats,
            date_col       = self.overview.get("date_col"),
            scenario       = "single"
        )