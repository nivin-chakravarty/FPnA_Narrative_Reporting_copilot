from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class MonthResponse(BaseModel):
    months: List[str]

class ReportResponse(BaseModel):
    month: str
    variance_analysis: List[Dict[str, Any]]
    top_drivers: List[Dict[str, Any]]
    draft_narrative: str
    review_mode: Dict[str, Any]
    leadership_summary: str
    logs: List[Dict[str, str]]
