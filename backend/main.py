from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import json

from backend.services.file_service import save_upload, load_three, unique_months
from backend.agents.fpa_agent import run_deterministic_agent_flow
from backend.utils.logger import add_log, get_logs, clear_logs

app = FastAPI(title="FP&A Narrative Reporting Copilot", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

STATE = {
    "actual_path": DATA_DIR / "pnl_actual.csv",
    "budget_path": DATA_DIR / "pnl_budget.csv",
    "forecast_path": DATA_DIR / "pnl_forecast.csv",
}
LAST_REPORT: dict = {}

@app.get("/")
def root():
    return {"message": "FP&A Narrative Reporting Copilot API running"}

@app.post("/upload-files")
def upload_files(
    actual: UploadFile = File(...),
    budget: UploadFile = File(...),
    forecast: UploadFile = File(...),
):
    clear_logs()
    add_log("Upload Started", "Receiving three separate files: Actual, Budget and Forecast")
    try:
        STATE["actual_path"] = save_upload(actual, "actual")
        STATE["budget_path"] = save_upload(budget, "budget")
        STATE["forecast_path"] = save_upload(forecast, "forecast")
        dfs = load_three(STATE["actual_path"], STATE["budget_path"], STATE["forecast_path"])
        months = unique_months(dfs)
        add_log("Input Validation", "CSV/XLSX files validated and month column extracted", "done")
        add_log("Upload Completed", "Files are ready for month selection", "done")
        return {"message": "Files uploaded successfully", "months": months, "logs": get_logs()}
    except Exception as e:
        add_log("Upload Failed", str(e), "error")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/months")
def months():
    try:
        dfs = load_three(STATE["actual_path"], STATE["budget_path"], STATE["forecast_path"])
        return {"months": unique_months(dfs)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/generate-report")
def generate_report(month: str = Form("All")):
    global LAST_REPORT
    clear_logs()
    add_log("Calling Agent", f"Planner started for selected month: {month}")
    try:
        dfs = load_three(STATE["actual_path"], STATE["budget_path"], STATE["forecast_path"])
        LAST_REPORT = run_deterministic_agent_flow(
            dfs["actual"].to_dict("records"),
            dfs["budget"].to_dict("records"),
            dfs["forecast"].to_dict("records"),
            month,
        )
        return LAST_REPORT
    except Exception as e:
        add_log("Report Failed", str(e), "error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/latest-report")
def latest_report():
    return LAST_REPORT or {"message": "No report generated yet."}

@app.get("/logs")
def logs():
    return {"logs": get_logs()}

@app.get("/download/{section}")
def download_section(section: str):
    if not LAST_REPORT:
        raise HTTPException(status_code=404, detail="Generate report first.")
    if section in ["variance_analysis", "top_drivers"]:
        path = DOWNLOAD_DIR / f"{section}.csv"
        pd.DataFrame(LAST_REPORT.get(section, [])).to_csv(path, index=False)
        return FileResponse(path, filename=path.name)
    if section in ["draft_narrative", "leadership_summary"]:
        path = DOWNLOAD_DIR / f"{section}.txt"
        path.write_text(str(LAST_REPORT.get(section, "")), encoding="utf-8")
        return FileResponse(path, filename=path.name)
    if section == "review_mode":
        path = DOWNLOAD_DIR / "review_mode.json"
        path.write_text(json.dumps(LAST_REPORT.get(section, {}), indent=2), encoding="utf-8")
        return FileResponse(path, filename=path.name)
    if section == "logs":
        path = DOWNLOAD_DIR / "logs.csv"
        pd.DataFrame(LAST_REPORT.get("logs", [])).to_csv(path, index=False)
        return FileResponse(path, filename=path.name)
    raise HTTPException(status_code=400, detail="Invalid section")
