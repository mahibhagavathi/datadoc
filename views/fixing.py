import streamlit as st
import pandas as pd
from utils.fixer import apply_fix
from utils.detector import compute_health_score


SEVERITY_COLORS = {
    "critical": "#dc3545",
    "high": "#fd7e14",
    "medium": "#e6a817",
    "low": "#0d6efd",
}

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}


def show_fixing():
    issues = st.session_state.issues
    idx = st.session_state.current_issue_idx

    # Check if all issues reviewed
    if idx >= len(issues):
        # Compute final score
        remaining = [i for i in issues if i.get("decision") != "apply"]
        st.session_state.health_score_after = compute_health_score(
            [i for i in issues if i.get("decision") == "skip" or not i.get("decision")]
        )
        st.session_state.phase = "results"
        st.rerun()
        return

    iss = issues[idx]
    total = len(issues)

    st.markdown(f"### 🛠️ Fix Review — Issue {idx + 1} of {total}")
    prog_val = idx / total
    st.progress(prog_val)

    # ── Jump to issue ─────────────────────────────────────────────────────────
    with st.expander("⬇️ Jump to a specific issue"):
        jump_options = {f"#{i['id']} {i['title']} ({i['column']})": i_idx
                        for i_idx, i in enumerate(issues)}
        jump_label = st.selectbox("Select issue:", list(jump_options.keys()), index=idx, label_visibility="collapsed")
        if st.button("Go"):
            st.session_state.current_issue_idx = jump_options[jump_label]
            st.rerun()

    st.divider()

    # ── Issue card ────────────────────────────────────────────────────────────
    sev = iss["severity"]
    color = SEVERITY_COLORS.get(sev, "#333")
    emoji = SEVERITY_EMOJI.get(sev, "")

    st.markdown(
        f"""<div style='border-left: 5px solid {color}; padding: 0.5rem 1rem; 
        background:#fafafa; border-radius:0 8px 8px 0; margin-bottom:1rem'>
        <span style='color:{color}; font-weight:700; font-size:1.1rem'>
        {emoji} {sev.upper()} — {iss['title']}</span><br>
        <span style='color:#666'>Column: <code>{iss['column']}</code></span>
        </div>""",
        unsafe_allow_html=True
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("**🔍 What was detected**")
        st.info(iss["detected"])

        st.markdown("**🤖 AI Explanation**")
        ai_exp = iss.get("ai_explanation") or "No AI explanation available."
        st.write(ai_exp)

        st.markdown("**🔧 Recommended Fix**")
        st.success(iss["recommended_fix"])

        st.markdown("**⚠️ Risk if Ignored**")
        risk = iss.get("ai_risk") or "Unknown — see detected description."
        st.warning(risk)

        conf = iss.get("ai_confidence", "N/A")
        conf_color = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(conf, "⚪")
        st.caption(f"AI Confidence: {conf_color} {conf}")

    with col_right:
        st.markdown("**📊 Before/After Preview**")
        df_raw = st.session_state.df_raw
        col_name = iss["column"]

        if col_name in df_raw.columns and col_name != "ALL" and col_name != "Multiple":
            try:
                before = df_raw[[col_name]].head(8).rename(columns={col_name: "Before"})
                after_df = apply_fix(df_raw.head(8), iss)
                if col_name in after_df.columns:
                    after = after_df[[col_name]].rename(columns={col_name: "After"})
                else:
                    after = pd.DataFrame({"After": ["(column removed)"] * len(before)})
                preview = pd.concat([before, after], axis=1)
                st.dataframe(preview, use_container_width=True, height=280)
            except Exception:
                st.caption("Preview not available for this fix type.")
        else:
            st.caption("This fix affects the whole dataset — no column preview available.")

    st.divider()

    # ── Decision buttons ──────────────────────────────────────────────────────
    st.markdown("**What would you like to do?**")

    btn_col1, btn_col2, btn_col3 = st.columns(3)

    with btn_col1:
        if st.button("✅ Apply Recommended Fix", use_container_width=True, type="primary"):
            _record_decision(idx, "apply", None)

    with btn_col2:
        if st.button("❌ Skip This Issue", use_container_width=True):
            _record_decision(idx, "skip", None)

    with btn_col3:
        show_custom = st.session_state.get("show_custom_input", False)
        if st.button("✏️ Enter Custom Fix", use_container_width=True):
            st.session_state.show_custom_input = not show_custom
            st.rerun()

    if st.session_state.get("show_custom_input", False):
        st.markdown("---")
        custom_val = st.text_input(
            "Describe your custom fix (e.g. 'Replace nulls with 0' or 'Drop the column'):",
            key=f"custom_input_{idx}"
        )
        if st.button("✏️ Apply Custom Fix", disabled=not custom_val):
            _record_decision(idx, "custom", custom_val)

    # ── Nav buttons ───────────────────────────────────────────────────────────
    st.markdown("---")
    nav1, nav2, nav3 = st.columns([1, 2, 1])

    with nav1:
        if idx > 0:
            if st.button("← Previous", use_container_width=True):
                st.session_state.current_issue_idx = idx - 1
                st.session_state.show_custom_input = False
                st.rerun()

    with nav2:
        reviewed = sum(1 for i in issues if i.get("decision"))
        st.caption(f"{reviewed}/{total} issues reviewed")

    with nav3:
        if idx < total - 1:
            if st.button("Next →", use_container_width=True):
                # Skip without decision
                if not iss.get("decision"):
                    _record_decision(idx, "skip", None)
                else:
                    st.session_state.current_issue_idx = idx + 1
                    st.session_state.show_custom_input = False
                    st.rerun()

    # ── Finish early button ───────────────────────────────────────────────────
    if reviewed > 0:
        st.markdown("---")
        if st.button("🏁 Finish & Download Results", use_container_width=True):
            # Mark remaining as skipped
            for i in issues:
                if not i.get("decision"):
                    i["decision"] = "skip"
            st.session_state.issues = issues
            st.session_state.phase = "results"
            st.rerun()


def _record_decision(idx: int, decision: str, custom_val):
    issues = st.session_state.issues
    issues[idx]["decision"] = decision
    if custom_val:
        issues[idx]["custom_value"] = custom_val

    # Apply fix to clean df
    if decision in ("apply", "custom"):
        df = st.session_state.df_clean
        df = apply_fix(df, issues[idx])
        st.session_state.df_clean = df

    st.session_state.issues = issues
    st.session_state.current_issue_idx = idx + 1
    st.session_state.show_custom_input = False
    st.rerun()
