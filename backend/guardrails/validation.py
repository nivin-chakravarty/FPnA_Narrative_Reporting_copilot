from __future__ import annotations
from typing import Dict, Any, List
import re

ALLOWED_TOPICS = ["actual", "budget", "forecast", "variance", "driver", "revenue", "cogs", "opex", "profit", "loss", "month", "category", "account", "inr", "lakhs", "leadership", "summary", "favourable", "unfavourable", "finance", "glossary", "policy", "review"]
BLOCKED_TERMS = ["password", "credit card", "medical", "legal advice", "politics"]
UNSUPPORTED_CAUSE_WORDS = ["demand", "campaign", "customer", "market", "pricing", "volume", "seasonality", "competition", "success"]

def input_validation(question: str) -> Dict[str, str]:
    q = (question or "").lower()
    if any(t in q for t in BLOCKED_TERMS):
        return {"allowed": "no", "reason": "Blocked by content/privacy moderation."}
    if not any(t in q for t in ALLOWED_TOPICS):
        return {"allowed": "no", "reason": "I dont know"}
    return {"allowed": "yes", "reason": "Allowed finance question."}

def regex_semantic_filter(text: str) -> Dict[str, Any]:
    issues = []
    if re.search(r"\b\d+(\.\d+)?\s*(crore|million|billion)\b", text.lower()):
        issues.append("Possible unsupported non-INR-lakhs amount detected.")
    if any(w in text.lower() for w in UNSUPPORTED_CAUSE_WORDS):
        issues.append("Possible unsupported business-cause claim detected.")
    return {"passed": not issues, "issues": issues}

def no_fabricated_numbers(answer: str, allowed_numbers: List[float]) -> Dict[str, Any]:
    nums = [float(x) for x in re.findall(r"[-+]?\d+\.\d+|[-+]?\d+", answer)]
    allowed = {round(float(x), 2) for x in allowed_numbers if x is not None}
    unknown = [n for n in nums if round(n, 2) not in allowed and n not in [1,2,3,100,150,2025,2026]]
    return {"passed": len(unknown) == 0, "unknown_numbers": unknown[:10]}

def review_mode_from_data(variance_records: list, draft_answer: str = "") -> Dict[str, Any]:
    flags, questions, ideas = [], [], []
    if not variance_records:
        flags.append("⚠ Month selected has no records.")
        questions.append("Can valid Actual, Budget and Forecast data be provided for the selected month?")
        return {"review_flags": flags, "follow_up_questions": questions, "ideas": ideas}
    missing_budget = [r for r in variance_records if r.get("budget") is None]
    missing_forecast = [r for r in variance_records if r.get("forecast") is None]
    missing_actual = [r for r in variance_records if r.get("actual") is None]
    blank_accounts = [r for r in variance_records if not str(r.get("account") or "").strip()]
    zero_budget = [r for r in variance_records if r.get("budget") == 0]
    if missing_budget: flags.append(f"⚠ Missing Budget values for {len(missing_budget)} accounts.")
    if missing_forecast: flags.append(f"⚠ Forecast data unavailable for {len(missing_forecast)} accounts.")
    if missing_actual: flags.append(f"⚠ Missing Actual values for {len(missing_actual)} accounts.")
    if blank_accounts: flags.append(f"⚠ Null or blank account values for {len(blank_accounts)} rows.")
    if zero_budget: flags.append(f"⚠ Budget contains zero for {len(zero_budget)} accounts; variance % skipped.")
    semantic = regex_semantic_filter(draft_answer)
    for issue in semantic["issues"]:
        flags.append(f"⚠ {issue}")
    if not flags:
        flags.append("No major data quality or unsupported-claim flags were detected from computed data.")
    questions.extend([
        "Do you have business context explaining the largest favourable or unfavourable driver?",
        "Should missing values be excluded or treated as zero for management reporting?",
        "Is there additional operating context for Revenue, COGS, or OPEX movements?",
    ])
    total_rev = sum((r.get("actual") or 0) for r in variance_records if str(r.get("category","")).lower()=="revenue")
    total_opex_var = sum((r.get("budget_variance") or 0) for r in variance_records if str(r.get("category","")).lower()=="opex")
    if total_rev:
        ideas.append("Review revenue accounts with negative budget variance and confirm whether pricing, volume, or mix context is available before adding business reasons.")
    if total_opex_var < 0:
        ideas.append("OPEX is unfavourable versus budget; check high-spend OPEX accounts for controllable cost actions.")
    else:
        ideas.append("OPEX is favourable or neutral versus budget; continue monitoring spend discipline while confirming business context.")
    return {"review_flags": flags, "follow_up_questions": questions, "ideas": ideas}
