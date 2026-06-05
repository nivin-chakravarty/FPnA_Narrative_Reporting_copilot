from __future__ import annotations
import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
GRADIO_URL = os.getenv("GRADIO_URL", "http://127.0.0.1:7860")

st.set_page_config(page_title="FP&A Narrative Reporting Copilot", page_icon="📊", layout="wide")

st.markdown(
    """
<style>
.stApp {
    background: radial-gradient(circle at top left, #eef7ff 0, #f7fbff 35%, #ffffff 70%);
}
.hero {
    padding: 24px 28px;
    border-radius: 22px;
    background: linear-gradient(135deg, #0f4c81 0%, #2b78c6 45%, #66b2ff 100%);
    color: white;
    box-shadow: 0 12px 35px rgba(15, 76, 129, 0.25);
    margin-bottom: 18px;
}
.hero h1 {font-size: 34px; margin:0;}
.hero p {font-size: 16px; margin-top:10px; opacity:.95;}
.card {
    padding: 18px;
    border-radius: 18px;
    background: rgba(255,255,255,.88);
    border: 1px solid rgba(15,76,129,.12);
    box-shadow: 0 8px 22px rgba(15,76,129,.08);
}
#chat-toggle {display:none;}
.chat-button {
    position:fixed; right:24px; bottom:24px; z-index:99999;
    background:linear-gradient(135deg,#0f4c81,#66b2ff); color:white;
    border-radius:50%; width:66px; height:66px; display:flex;
    align-items:center; justify-content:center; font-size:31px; cursor:pointer;
    box-shadow:0 8px 24px rgba(0,0,0,.28);
}
.chat-popup {
    display:none; position:fixed; right:24px; bottom:102px; z-index:99998;
    width:420px; height:560px; background:white; border-radius:18px;
    border:1px solid #d9e6f2; box-shadow:0 12px 38px rgba(0,0,0,.28); overflow:hidden;
}
#chat-toggle:checked ~ .chat-popup {display:block;}
.chat-popup iframe {width:100%; height:100%; border:0;}
</style>
<div class="hero">
  <h1>📊 FP&A Narrative Reporting Copilot</h1>
  <p>Upload Actual, Budget and Forecast files, select month, compute variance, generate grounded narrative, review flags and leadership summary.</p>
</div>
<input type="checkbox" id="chat-toggle" />
<label class="chat-button" for="chat-toggle">💬</label>
<div class="chat-popup"><iframe src="%s"></iframe></div>
""" % GRADIO_URL,
    unsafe_allow_html=True,
)

left, right = st.columns([1.15, 1])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1️⃣ Upload P&L Files")
    st.caption("Upload all three files separately. Supported formats: CSV, XLSX, XLS.")
    actual = st.file_uploader("Actual file", type=["csv", "xlsx", "xls"], key="actual_file")
    budget = st.file_uploader("Budget file", type=["csv", "xlsx", "xls"], key="budget_file")
    forecast = st.file_uploader("Forecast file", type=["csv", "xlsx", "xls"], key="forecast_file")
    if st.button("Upload & Read Unique Months", type="primary", use_container_width=True):
        if not (actual and budget and forecast):
            st.error("Please upload Actual, Budget and Forecast files separately.")
        else:
            files = {
                "actual": (actual.name, actual.getvalue()),
                "budget": (budget.name, budget.getvalue()),
                "forecast": (forecast.name, forecast.getvalue()),
            }
            try:
                res = requests.post(f"{API_URL}/upload-files", files=files, timeout=180)
                res.raise_for_status()
                payload = res.json()
                st.session_state.months = payload.get("months", ["All"])
                st.session_state.upload_logs = payload.get("logs", [])
                st.success("Files uploaded and months loaded successfully.")
            except Exception as e:
                st.error(f"Upload failed: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2️⃣ Select Month")
    if "months" not in st.session_state:
        try:
            st.session_state.months = requests.get(f"{API_URL}/months", timeout=20).json().get("months", ["All"])
        except Exception:
            st.session_state.months = ["All"]
    month = st.selectbox("Unique month values from uploaded files", st.session_state.months)
    run = st.button("Generate Dashboard Result", type="primary", use_container_width=True)
    st.info("Results will appear below in tabs after the FP&A agent runs.")
    st.markdown('</div>', unsafe_allow_html=True)

if run:
    with st.status("Running FP&A agent and tools...", expanded=True) as status:
        st.write("Calling Agent")
        st.write("Calling tools: variance calculation and top driver detection")
        try:
            response = requests.post(f"{API_URL}/generate-report", data={"month": month}, timeout=300)
            response.raise_for_status()
            st.session_state.report = response.json()
            status.update(label="Report generated successfully", state="complete")
        except Exception as e:
            status.update(label="Report failed", state="error")
            st.error(str(e))

report = st.session_state.get("report")
if report:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Variance Analysis", "Top Drivers", "Draft Narrative", "Review Mode", "Leadership Summary", "Logger"
    ])

    with tab1:
        st.subheader("Variance Analysis")
        df = pd.DataFrame(report.get("variance_analysis", []))
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download Variance Analysis CSV", df.to_csv(index=False), "variance_analysis.csv", "text/csv")

    with tab2:
        st.subheader("Top Drivers")
        td = pd.DataFrame(report.get("top_drivers", []))
        st.dataframe(td, use_container_width=True, hide_index=True)
        if not td.empty and {"account", "budget_variance"}.issubset(td.columns):
            st.bar_chart(td.set_index("account")["budget_variance"])
        st.download_button("⬇️ Download Top Drivers CSV", td.to_csv(index=False), "top_drivers.csv", "text/csv")

    with tab3:
        st.subheader("Draft Narrative")
        text = report.get("draft_narrative", "")
        st.markdown(text)
        st.download_button("⬇️ Download Draft Narrative", text, "draft_narrative.txt")

    with tab4:
        st.subheader("Review Mode")
        review = report.get("review_mode", {})
        st.markdown("### Review Flags")
        for f in review.get("review_flags", []):
            st.warning(f)
        st.markdown("### Follow-up Questions")
        for i, q in enumerate(review.get("follow_up_questions", []), 1):
            st.write(f"{i}. {q}")
        st.markdown("### Ideas")
        for idea in review.get("ideas", []):
            st.info(idea)
        st.download_button("⬇️ Download Review Mode", str(review), "review_mode.txt")

    with tab5:
        st.subheader("Leadership Summary")
        summary = report.get("leadership_summary", "")
        st.markdown(summary)
        st.download_button("⬇️ Download Leadership Summary", summary, "leadership_summary.txt")

    with tab6:
        st.subheader("Logger")
        logs = pd.DataFrame(report.get("logs", []))
        st.dataframe(logs, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download Logs CSV", logs.to_csv(index=False), "logs.csv", "text/csv")
