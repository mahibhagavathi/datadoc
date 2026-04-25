import streamlit as st
import pandas as pd
import json
from datetime import datetime
from utils.detector import compute_health_score
from utils.report import generate_pdf


DECISION_LABELS = {
    "apply": "✅ Applied",
    "skip": "❌ Skipped",
    "custom": "✏️ Custom Fix",
}


def show_results():
    st.title("✅ Cleaning Complete!")

    issues = st.session_state.issues
    df_raw = st.session_state.df_raw
    df_clean = st.session_state.df_clean
    score_before = st.session_state.health_score_before

    applied = [i for i in issues if i.get("decision") == "apply"]
    skipped = [i for i in issues if i.get("decision") == "skip"]
    custom = [i for i in issues if i.get("decision") == "custom"]
    remaining_issues = skipped  # fixes not applied
    score_after = compute_health_score(remaining_issues)
    st.session_state.health_score_after = score_after

    # ── Score comparison ──────────────────────────────────────────────────────
    st.markdown("### 📊 Before vs After Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Health Score Before", f"{score_before}/100")
    col2.metric("Health Score After", f"{score_after}/100", delta=f"+{score_after - score_before}")
    col3.metric("Issues Fixed", f"{len(applied) + len(custom)}/{len(issues)}")

    st.divider()

    # ── Stats table ───────────────────────────────────────────────────────────
    rows = []
    metrics = {
        "Total Rows": (df_raw.shape[0], df_clean.shape[0]),
        "Total Columns": (df_raw.shape[1], df_clean.shape[1]),
        "Missing Values": (int(df_raw.isna().sum().sum()), int(df_clean.isna().sum().sum())),
        "Duplicate Rows": (int(df_raw.duplicated().sum()), int(df_clean.duplicated().sum())),
    }

    for metric, (before, after) in metrics.items():
        rows.append({
            "Metric": metric,
            "Before": f"{before:,}",
            "After": f"{after:,}",
            "Change": f"{after - before:+,}" if before != after else "—",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Change log ────────────────────────────────────────────────────────────
    with st.expander(f"📋 Full Change Log ({len(issues)} issues)"):
        for iss in issues:
            decision = iss.get("decision", "pending")
            label = DECISION_LABELS.get(decision, decision)
            custom_note = f" → '{iss['custom_value']}'" if iss.get("custom_value") else ""
            st.markdown(f"{label} **#{iss['id']}** `{iss['column']}` — {iss['title']}{custom_note}")

    st.divider()

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown("### 📦 Download Your Files")

    dl1, dl2, dl3 = st.columns(3)

    with dl1:
        csv_data = df_clean.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ cleaned_data.csv",
            data=csv_data,
            file_name="cleaned_data.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )
        st.caption("Your cleaned dataset, ready for analysis.")

    with dl2:
        try:
            pdf_bytes = generate_pdf(
                dataset_name=st.session_state.dataset_name,
                df_raw=df_raw,
                df_clean=df_clean,
                issues=issues,
                score_before=score_before,
                score_after=score_after,
            )
            st.download_button(
                label="⬇️ audit_report.pdf",
                data=pdf_bytes,
                file_name="datadoctor_audit_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.caption("Full audit trail — great for compliance or team handoffs.")
        except Exception as e:
            st.warning(f"PDF generation failed: {e}")

    with dl3:
        log = {
            "generated_at": datetime.now().isoformat(),
            "dataset": st.session_state.dataset_name,
            "score_before": score_before,
            "score_after": score_after,
            "issues": [
                {
                    "id": i["id"],
                    "title": i["title"],
                    "column": i["column"],
                    "severity": i["severity"],
                    "decision": i.get("decision"),
                    "custom_value": i.get("custom_value"),
                }
                for i in issues
            ],
        }
        st.download_button(
            label="⬇️ cleaning_log.json",
            data=json.dumps(log, indent=2).encode("utf-8"),
            file_name="cleaning_log.json",
            mime="application/json",
            use_container_width=True,
        )
        st.caption("Machine-readable log — useful for automated pipelines.")

    st.divider()

    # ── Preview clean data ────────────────────────────────────────────────────
    with st.expander("👀 Preview Cleaned Dataset"):
        st.dataframe(df_clean.head(20), use_container_width=True)

    # ── Reset ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("🔄 Clean Another Dataset", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        from utils.session import init_session
        init_session()
        st.rerun()
