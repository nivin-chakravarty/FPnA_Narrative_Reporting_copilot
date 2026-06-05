from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import pandas as pd

REQUIRED_COLUMNS = {"month", "category", "account"}
AMOUNT_ALIASES = ["amount_inr_lakhs", "amount", "value"]
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

def _read_any(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        raise ValueError("Only CSV/XLSX/XLS files are allowed.")
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    amount_col = next((c for c in AMOUNT_ALIASES if c in df.columns), None)
    if not amount_col:
        raise ValueError("Missing amount column. Use amount_inr_lakhs or amount.")
    df = df.rename(columns={amount_col: "amount_inr_lakhs"})
    df["month"] = df["month"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["account"] = df["account"].astype(str).str.strip()
    df["amount_inr_lakhs"] = pd.to_numeric(df["amount_inr_lakhs"], errors="coerce")
    return df[["month", "category", "account", "amount_inr_lakhs"]]

def save_upload(file, name: str) -> Path:
    ext = Path(file.filename).suffix.lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise ValueError("Upload must be CSV/XLSX/XLS.")
    out = UPLOAD_DIR / f"{name}{ext}"
    with open(out, "wb") as f:
        f.write(file.file.read())
    return out

def load_three(actual_path: str | Path, budget_path: str | Path, forecast_path: str | Path) -> Dict[str, pd.DataFrame]:
    return {"actual": _read_any(actual_path), "budget": _read_any(budget_path), "forecast": _read_any(forecast_path)}

def unique_months(dfs: Dict[str, pd.DataFrame]) -> List[str]:
    months = sorted(set().union(*[set(df["month"].dropna().astype(str)) for df in dfs.values()]))
    return ["All"] + months
