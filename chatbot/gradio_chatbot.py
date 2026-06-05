from __future__ import annotations
import os
import sys
import json
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import gradio as gr
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from backend.guardrails.validation import input_validation, regex_semantic_filter, no_fabricated_numbers
from backend.services.rag import retrieve_context, read_context
from backend.utils.logger import add_log
from backend.utils.langfuse_client import get_langfuse_handler

load_dotenv()
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")


def get_latest_report_context() -> str:
    try:
        report = requests.get(f"{FASTAPI_URL}/latest-report", timeout=8).json()
    except Exception:
        report = {"message": "No report generated yet."}
    glossary, policy = read_context()
    compact_report = {
        "month": report.get("month"),
        "computed_financial_data": report.get("variance_analysis", [])[:20],
        "top_drivers": report.get("top_drivers", []),
        "draft_narrative": report.get("draft_narrative", ""),
        "leadership_summary": report.get("leadership_summary", ""),
        "review_mode": report.get("review_mode", {}),
    }
    return (
        "Finance glossary:\n" + glossary +
        "\n\nAccounting policy notes:\n" + policy +
        "\n\nComputed financial data and summaries:\n" + json.dumps(compact_report, indent=2)
    )


def chat(message, history):
    add_log("Chatbot", "Received chatbot question")
    check = input_validation(message)
    if check["allowed"] != "yes":
        add_log("Chatbot Guardrail", "Question blocked or outside uploaded finance context", "warning")
        return "I dont know"

    rag_context = retrieve_context(message)
    runtime_context = get_latest_report_context()
    prompt = f"""
You are an FP&A grounded chatbot.
Answer ONLY from these sources:
1. Computed financial data
2. Draft narrative and leadership summary
3. Finance glossary
4. Accounting policy notes

If the answer is not present, reply exactly: I dont know
Do not invent numbers, causes, strategy, or business context.
Use INR lakhs when discussing values.

RAG Context:
{rag_context}

Runtime Context:
{runtime_context}

Question: {message}
"""
    try:
        llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )
        handler = get_langfuse_handler()
        config = {"callbacks": [handler]} if handler else None
        ans = llm.invoke(prompt, config=config).content.strip()
    except Exception:
        add_log("Chatbot LLM", "LLM unavailable; returning fallback", "warning")
        ans = "I dont know"

    semantic = regex_semantic_filter(ans)
    if not semantic["passed"] and "requires confirmation" not in ans.lower():
        add_log("Chatbot Guardrail", "Unsupported cause or unsafe output detected", "warning")
        return "I dont know"

    report_text = runtime_context
    allowed_numbers = [float(x) for x in __import__("re").findall(r"[-+]?\d+\.\d+|[-+]?\d+", report_text)]
    verified = no_fabricated_numbers(ans, allowed_numbers)
    if not verified["passed"]:
        add_log("Chatbot Verification", "Possible fabricated number detected", "warning")
        return "I dont know"

    add_log("Chatbot", "Answer generated from grounded context", "done")
    return ans


demo = gr.ChatInterface(
    fn=chat,
    title="FP&A Grounded Chatbot",
    description="Answers only from uploaded P&L results, finance glossary, and accounting policy notes. If unsupported, it replies: I dont know.",
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
