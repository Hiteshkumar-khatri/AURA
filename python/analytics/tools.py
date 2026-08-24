import pandas as pd
import numpy as np
from datetime import datetime

class AuraTools:

    def __init__(self, df: pd.DataFrame, filename: str):
        self.df       = df.copy()
        self.filename = filename
        self.log      = []

        self.date_col = None
        for col in self.df.columns:
            if any(kw in col.lower() for kw in ["date","time","month","year"]):
                try:
                    self.df[col] = pd.to_datetime(self.df[col], errors="coerce")
                    if self.df[col].notna().sum() > 0:
                        self.date_col = col
                        break
                except:
                    pass

        self.numeric_cols = self.df.select_dtypes(include="number").columns.tolist()
        self.cat_cols = self.df.select_dtypes(include="object").columns.tolist()
        if self.date_col in self.cat_cols:
            self.cat_cols.remove(self.date_col)

    def _log(self, tool, params, result_summary):
        self.log.append({
            "tool":   tool,
            "params": params,
            "result": result_summary,
            "time":   datetime.now().strftime("%H:%M:%S")
        })

    def get_overview(self):
        result = {
            "rows":         len(self.df),
            "columns":      len(self.df.columns),
            "numeric_cols": self.numeric_cols,
            "cat_cols":     self.cat_cols,
            "date_col":     self.date_col,
            "duplicates":   int(self.df.duplicated().sum()),
        }
        self._log("get_overview", {}, f"{result['rows']} rows, {result['columns']} cols")
        return result

    def get_column_stats(self, column: str):
        if column not in self.df.columns:
            return {"error": f"Column '{column}' not found"}
        col = self.df[column]
        if pd.api.types.is_numeric_dtype(col):
            result = {
                "column": column, "type": "numeric",
                "count": int(col.count()), "missing": int(col.isnull().sum()),
                "missing_pct": round(col.isnull().sum() / len(col) * 100, 2),
                "mean": round(float(col.mean()), 2),
                "median": round(float(col.median()), 2),
                "std": round(float(col.std()), 2),
                "min": round(float(col.min()), 2),
                "max": round(float(col.max()), 2),
                "q25": round(float(col.quantile(0.25)), 2),
                "q75": round(float(col.quantile(0.75)), 2),
            }
        else:
            vc = col.value_counts()
            result = {
                "column": column, "type": "categorical",
                "count": int(col.count()), "missing": int(col.isnull().sum()),
                "missing_pct": round(col.isnull().sum() / len(col) * 100, 2),
                "unique": int(col.nunique()),
                "top_values": vc.head(5).to_dict(),
                "most_common": str(vc.index[0]) if len(vc) > 0 else None,
            }
        self._log("get_column_stats", {"column": column}, str(result))
        return result

    def group_by(self, metric: str, group: str, agg: str = "sum", top_n: int = 10):
        if metric not in self.df.columns:
            return {"error": f"Metric column '{metric}' not found"}
        if group not in self.df.columns:
            return {"error": f"Group column '{group}' not found"}
        agg_func = {"sum": "sum", "mean": "mean", "count": "count"}.get(agg, "sum")
        result_df = self.df.groupby(group)[metric].agg(agg_func).reset_index()
        result_df.columns = [group, "value"]
        result_df = result_df.sort_values("value", ascending=False).head(top_n)
        result_df["value"] = result_df["value"].round(2)
        result = {"metric": metric, "group": group, "agg": agg, "data": result_df.to_dict(orient="records")}
        self._log("group_by", {"metric": metric, "group": group}, f"Top: {result_df.iloc[0][group]}={result_df.iloc[0]['value']}")
        return result

    def compare_periods(self, metric: str, period1: str, period2: str):
        if not self.date_col:
            return {"error": "No date column detected"}
        if metric not in self.df.columns:
            return {"error": f"Metric '{metric}' not found"}
        df = self.df.copy()
        df["_period"] = df[self.date_col].dt.to_period("M").astype(str)
        p1_data = df[df["_period"] == period1][metric]
        p2_data = df[df["_period"] == period2][metric]
        if len(p1_data) == 0:
            return {"error": f"No data found for period '{period1}'"}
        if len(p2_data) == 0:
            return {"error": f"No data found for period '{period2}'"}
        p1_val = round(float(p1_data.sum()), 2)
        p2_val = round(float(p2_data.sum()), 2)
        change = round(p2_val - p1_val, 2)
        pct = round((change / p1_val * 100), 2) if p1_val != 0 else 0
        result = {
            "metric": metric, "period1": period1, "period2": period2,
            "p1_value": p1_val, "p2_value": p2_val,
            "change": change, "change_pct": pct,
            "direction": "increase" if change > 0 else "decrease"
        }
        self._log("compare_periods", {"metric": metric, "p1": period1, "p2": period2}, f"{period1}={p1_val} -> {period2}={p2_val} ({pct}%)")
        return result

    def monthly_trend(self, metric: str):
        if not self.date_col:
            return {"error": "No date column detected"}
        if metric not in self.df.columns:
            return {"error": f"Metric '{metric}' not found"}
        df = self.df.copy()
        df["_month"] = df[self.date_col].dt.to_period("M").astype(str)
        trend = df.groupby("_month")[metric].sum().reset_index()
        trend.columns = ["month", "value"]
        trend["value"] = trend["value"].round(2)
        trend["mom_change_pct"] = trend["value"].pct_change().round(4) * 100
        best = trend.loc[trend["value"].idxmax()]
        worst = trend.loc[trend["value"].idxmin()]
        result = {
            "metric": metric,
            "months": trend.to_dict(orient="records"),
            "best_month": {"month": str(best["month"]), "value": float(best["value"])},
            "worst_month": {"month": str(worst["month"]), "value": float(worst["value"])},
            "total": round(float(trend["value"].sum()), 2),
            "avg_monthly": round(float(trend["value"].mean()), 2),
        }
        self._log("monthly_trend", {"metric": metric}, f"Best: {best['month']}={best['value']}")
        return result

    def detect_anomalies(self, metric: str, threshold: float = 2.0):
        if metric not in self.df.columns:
            return {"error": f"Metric '{metric}' not found"}
        col = self.df[metric].dropna()
        mean = float(col.mean())
        std = float(col.std())
        if std == 0:
            return {"metric": metric, "anomalies": [], "message": "No variance"}
        anomalies = []
        for idx, val in col.items():
            z = (val - mean) / std
            if abs(z) >= threshold:
                anomalies.append({"index": int(idx), "value": round(float(val), 2), "z_score": round(float(z), 2), "direction": "high" if z > 0 else "low"})
        anomalies.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        result = {"metric": metric, "mean": round(mean, 2), "std": round(std, 2), "threshold": threshold, "count": len(anomalies), "anomalies": anomalies[:10]}
        self._log("detect_anomalies", {"metric": metric}, f"Found {len(anomalies)} anomalies")
        return result

    def calculate_correlation(self, col1: str, col2: str):
        if col1 not in self.df.columns:
            return {"error": f"Column '{col1}' not found"}
        if col2 not in self.df.columns:
            return {"error": f"Column '{col2}' not found"}
        corr = self.df[[col1, col2]].dropna().corr().iloc[0, 1]
        corr = round(float(corr), 4)
        strength = "strong" if abs(corr) >= 0.7 else "moderate" if abs(corr) >= 0.4 else "weak"
        direction = "positive" if corr > 0 else "negative"
        result = {"col1": col1, "col2": col2, "correlation": corr, "strength": strength, "direction": direction, "interpretation": f"{strength} {direction} correlation between {col1} and {col2}"}
        self._log("calculate_correlation", {"col1": col1, "col2": col2}, f"r={corr}")
        return result

    def top_contributors(self, metric: str, group: str, top_n: int = 5):
        result = self.group_by(metric, group, "sum", top_n)
        if "error" in result:
            return result
        total = sum(r["value"] for r in result["data"])
        for r in result["data"]:
            r["pct_of_total"] = round(r["value"] / total * 100, 1) if total else 0
        result["total"] = round(total, 2)
        result["interpretation"] = f"Top {len(result['data'])} {group} groups account for {sum(r['pct_of_total'] for r in result['data']):.1f}% of total {metric}"
        self._log("top_contributors", {"metric": metric, "group": group}, result["interpretation"])
        return result

    def get_available_periods(self):
        if not self.date_col:
            return {"error": "No date column detected"}
        periods = self.df[self.date_col].dt.to_period("M").astype(str).unique().tolist()
        periods = sorted([p for p in periods if p != "NaT"])
        result = {"date_col": self.date_col, "periods": periods, "count": len(periods), "earliest": periods[0] if periods else None, "latest": periods[-1] if periods else None}
        self._log("get_available_periods", {}, f"{len(periods)} periods")
        return result

    def get_audit_trail(self):
        return self.log
