from __future__ import annotations
import logging, os, time
from pathlib import Path
from typing import List, Dict, Optional

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger("fpa_copilot")

_RUNTIME_LOGS: List[Dict[str, str]] = []

def add_log(stage: str, detail: str, status: str = "running") -> None:
    row = {"time": time.strftime("%H:%M:%S"), "stage": stage, "detail": detail, "status": status}
    _RUNTIME_LOGS.append(row)
    logger.info("%s | %s | %s", stage, detail, status)

def get_logs() -> List[Dict[str, str]]:
    return list(_RUNTIME_LOGS[-300:])

def clear_logs() -> None:
    _RUNTIME_LOGS.clear()
