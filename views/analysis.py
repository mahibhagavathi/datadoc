import streamlit as st
import time
from utils.detector import detect_issues, compute_health_score
from utils.ai import enrich_issue_with_ai


SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}


def show_analysis():
    st.title("🔍 Data Health Analysis")

    df = st.session_state.df_raw

    if not st.session_state.issues:
        _run_analysis(df)
    else:
        _show_scorecard()


def _run_analysis(df):
    st.markdown("Running quality checks across all 50 issue types...")

    progress = st.progress(0)
    status = st.empty()
    steps = [
        (0.10, "🔍 Scanning for structural issues..."),
        (0.25, "🔍 Checking for duplicates and integrity violations..."),
        (0.40, "🔍 Detecting missing values and type errors..."),
        (0.55, "🔍 Identifying outliers and impossible values..."),
        (0.70, "🔍 Checking formatting consistency..."),
        (0.85, "🤖 Asking Gemini AI for insights..."),
        (1.00, "✅ Analysis complete!"),
    ]

    for pct, msg in steps[:-2]:
        status.info(msg)
        progress.progress(pct)
        time.sleep(0.4)

    # Run the detection engine
    issues = detect_issues(df)
    score_before = compute_health_score(issues)
    st.session_state.health_score_before = score_before

    # Enrich with AI (show progress per issue, batch up to 10 for speed)
    status.info(steps[-2][1])
    progress.progress(0.85)

    enriched = []
    ai_sample = issues[:15]  # Only AI-enrich the first 15 for speed/quota
    for i, iss in enumerate(ai_sample):
        iss = enrich_issue_with_ai(iss)
        enriched.append(iss)
        progress.progress(0.85 + 0.15 * ((i + 1) / len(ai_sample)))

    # Remaining issues without AI
    for iss in issues[15:]:
        iss["ai_explanation"] = "AI enrichment skipped for speed (only first 15 issues enriched)."
        iss["ai_risk"] = "See detected description above."
        iss["ai_confidence"] = "N/A"
        enriched.append(iss)

    st.session_state.issues = enriched
    st.session_state.health_score_after = score_before  # will update as fixes applied

    status.success(steps[-1][1])
    progress.progress(1.0)
    time.sleep(0.5)
    st.rerun()


def _show_scorecard():
    issues = st.session_state.issues
    score = st.session_state.health_score_before

    # ── Health score ──────────────────────────────────────────────────────────
    st.markdown("### 📋 Data Health Scorecard")
    col_score, col_bar = st.columns([1, 3])

    color = "#dc3545" if score < 50 else "#fd7e14" if score < 70 else "#198754"
    col_score.markdown(
        f"<h1 style='color:{color}; font-size:3rem; margin:0'>{score}<span style='font-size:1.2rem'>/100</span></h1>",
        unsafe_allow_html=True
    )
    col_score.caption("Overall Health Score")
    col_bar.markdown("<br>", unsafe_allow_html=True)
    col_bar.progress(score / 100)

    st.divider()

    # ── Severity breakdown ────────────────────────────────────────────────────
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for iss in issues:
        counts[iss["severity"]] = counts.get(iss["severity"], 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Critical", counts["critical"])
    c2.metric("🟠 High", counts["high"])
    c3.metric("🟡 Medium", counts["medium"])
    c4.metric("🔵 Low", counts["low"])

    st.divider()

    # ── Issues table ──────────────────────────────────────────────────────────
    st.markdown(f"### {len(issues)} Issues Found")
    st.caption("Issues are ordered by severity. Click **Start Fixing** below to review each one.")

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(issues, key=lambda x: sev_order.get(x["severity"], 9))

    rows = []
    for iss in sorted_issues:
        rows.append({
            "Severity": f"{SEVERITY_EMOJI[iss['severity']]} {iss['severity'].title()}",
            "#": iss["id"],
            "Issue": iss["title"],
            "Column": iss["column"],
            "Detected": iss["detected"][:80] + "..." if len(iss["detected"]) > 80 else iss["detected"],
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    if st.button("🛠️ Start Fixing Issues", type="primary", use_container_width=True):
        st.session_state.current_issue_idx = 0
        st.session_state.phase = "fixing"
        st.rerun()
