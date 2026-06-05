from __future__ import annotations
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from langchain_core.tools import tool
from backend.utils.logger import add_log

MERGE_KEYS = ["month", "category", "account"]

def _safe_pct(delta: float, base: float):
    if pd.isna(base) or base == 0:
        return None
    return round((delta / abs(base)) * 100, 2)

def _favourability(category: str, variance: float) -> str:
    cat = str(category).lower()
    if "revenue" in cat:
        return "Favourable" if variance >= 0 else "Unfavourable"
    return "Favourable" if variance >= 0 else "Unfavourable"  # since costs are negative: less negative is favourable

@tool
def get_unique_months_tool(actual_records: list, budget_records: list, forecast_records: list) -> list:
    """Return unique months from uploaded Actual, Budget and Forecast records."""
    add_log("Calling tool", "get_unique_months_tool")
    dfs = [pd.DataFrame(x) for x in [actual_records, budget_records, forecast_records]]
    months = sorted(set().union(*[set(df["month"].astype(str)) for df in dfs if not df.empty]))
    add_log("Tool completed", "get_unique_months_tool", "done")
    return ["All"] + months

@tool
def compute_variance_table_tool(actual_records: list, budget_records: list, forecast_records: list, selected_month: str = "All") -> list:
    """Compute Actual, Budget, Forecast, Budget variance, variance %, Forecast variance and forecast variance %."""
    add_log("Calling tool", "compute_variance_table_tool")
    actual = pd.DataFrame(actual_records).rename(columns={"amount_inr_lakhs": "actual"})
    budget = pd.DataFrame(budget_records).rename(columns={"amount_inr_lakhs": "budget"})
    forecast = pd.DataFrame(forecast_records).rename(columns={"amount_inr_lakhs": "forecast"})
    if selected_month != "All":
        actual = actual[actual["month"].astype(str) == selected_month]
        budget = budget[budget["month"].astype(str) == selected_month]
        forecast = forecast[forecast["month"].astype(str) == selected_month]
    merged = actual[MERGE_KEYS + ["actual"]].merge(budget[MERGE_KEYS + ["budget"]], on=MERGE_KEYS, how="outer")
    merged = merged.merge(forecast[MERGE_KEYS + ["forecast"]], on=MERGE_KEYS, how="outer")
    for c in ["actual", "budget", "forecast"]:
        merged[c] = pd.to_numeric(merged[c], errors="coerce")
    merged["budget_variance"] = (merged["actual"] - merged["budget"]).round(2)
    merged["budget_variance_pct"] = merged.apply(lambda r: _safe_pct(r["budget_variance"], r["budget"]), axis=1)
    merged["forecast_variance"] = (merged["actual"] - merged["forecast"]).round(2)
    merged["forecast_variance_pct"] = merged.apply(lambda r: _safe_pct(r["forecast_variance"], r["forecast"]), axis=1)
    merged["favourability"] = merged.apply(lambda r: _favourability(r["category"], r["budget_variance"] if pd.notna(r["budget_variance"]) else 0), axis=1)
    merged = merged.replace({np.nan: None})
    add_log("Tool completed", "compute_variance_table_tool", "done")
    return merged.to_dict(orient="records")

@tool
def identify_top_drivers_tool(variance_records: list, top_n: int = 3) -> list:
    """Identify top drivers by absolute budget variance."""
    add_log("Calling tool", "identify_top_drivers_tool")
    df = pd.DataFrame(variance_records)
    if df.empty or "budget_variance" not in df.columns:
        return []
    df["abs_variance"] = pd.to_numeric(df["budget_variance"], errors="coerce").abs()
    out = df.sort_values("abs_variance", ascending=False).head(top_n).drop(columns=["abs_variance"], errors="ignore")
    add_log("Tool completed", "identify_top_drivers_tool", "done")
    return out.to_dict(orient="records")
