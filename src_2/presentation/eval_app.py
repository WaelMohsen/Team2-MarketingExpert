"""Streamlit dashboard for narrative-quality evaluations and their history."""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src_2.application import run_completed_cycle
from src_2.evaluation import NarrativeEvaluator, load_history, save_evaluation
from src_2.paths import INPUT_DIR

load_dotenv(ROOT / ".env")

CHECK_ICON = {True: "✅", False: "❌"}


def _configure_page() -> None:
    st.set_page_config(page_title="Narrative Evaluation", page_icon=":material/fact_check:", layout="wide")


def _sidebar() -> str:
    with st.sidebar:
        st.header("Evaluation controls")
        input_directory = st.text_input("Input directory", value=str(INPUT_DIR))
        st.caption(
            "A new run generates the LLM narrative for the cycle, then scores it with the "
            "deterministic consistency checker. The full LLM narrative makes ~14 model calls "
            "(several minutes)."
        )
        if st.button("Run new evaluation", icon=":material/play_arrow:", type="primary", use_container_width=True):
            try:
                with st.spinner("Generating narrative and evaluating..."):
                    report = run_completed_cycle(input_directory)
                    evaluation = NarrativeEvaluator().evaluate(report)
                    path = save_evaluation(evaluation)
                st.success(f"Saved run {evaluation.run_id} ({path.name}).")
            except Exception as exc:
                st.error(f"Evaluation run failed: {exc}")
        if st.button("Refresh history", icon=":material/refresh:", use_container_width=True):
            st.rerun()
        st.caption("Consistency 'hard' checks fail a campaign; 'warn' checks are advisory.")
    return input_directory


def _history_frame(history) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "run_timestamp": r.run_timestamp,
                "cycle_id": r.cycle_id,
                "model": r.model,
                "prompt_version": r.prompt_version,
                "campaigns": r.campaigns_evaluated,
                "consistency_pass_rate": r.consistency_pass_rate,
                "mean_overall_score": r.mean_overall_score,
                "run_id": r.run_id,
            }
            for r in history
        ]
    )


def _history_view(history) -> None:
    frame = _history_frame(history)
    st.subheader("Quality over time")
    if len(frame) < 2:
        st.info("Add more runs to see a trend. One run is shown below.")
    trend = frame.copy()
    trend["run_timestamp"] = pd.to_datetime(trend["run_timestamp"])
    chart = (
        alt.Chart(trend)
        .mark_line(point=True)
        .encode(
            x=alt.X("run_timestamp:T", title="Run"),
            y=alt.Y("consistency_pass_rate:Q", title="Consistency pass rate", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("model:N", title="Model"),
            strokeDash=alt.StrokeDash("prompt_version:N", title="Prompt version"),
            tooltip=["run_timestamp:T", "model:N", "prompt_version:N", "consistency_pass_rate:Q"],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, use_container_width=True)
    if trend["mean_overall_score"].notna().any():
        st.subheader("LLM judge mean score over time")
        judge = (
            alt.Chart(trend)
            .mark_line(point=True, color="#2E8B57")
            .encode(
                x=alt.X("run_timestamp:T", title="Run"),
                y=alt.Y("mean_overall_score:Q", title="Mean judge score (1-5)", scale=alt.Scale(domain=[1, 5])),
                tooltip=["run_timestamp:T", "mean_overall_score:Q"],
            )
            .properties(height=280)
        )
        st.altair_chart(judge, use_container_width=True)
    st.subheader("All runs")
    st.dataframe(frame.iloc[::-1], hide_index=True, use_container_width=True)


def _run_detail_view(history) -> None:
    labels = {
        f"{r.run_timestamp} · {r.model} · {r.prompt_version} · pass {r.consistency_pass_rate:.0%}": r
        for r in reversed(history)
    }
    selected = st.selectbox("Run", list(labels))
    report = labels[selected]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Campaigns", report.campaigns_evaluated)
    c2.metric("Consistency pass rate", f"{report.consistency_pass_rate:.0%}")
    c3.metric("Mean judge score", "n/a" if report.mean_overall_score is None else f"{report.mean_overall_score:.2f}")
    c4.metric("Prompt version", report.prompt_version)

    st.caption("Each campaign shows the evidence given to the model (input), the narrative it produced (output), and the verdict.")
    for ev in report.campaign_evaluations:
        flag = "✅" if ev.consistency_passed else "❌"
        with st.expander(f"{flag} {ev.campaign_name}"):
            col_in, col_out, col_verdict = st.columns([1, 1.1, 1])
            with col_in:
                st.markdown("**Input — evidence**")
                summary = ev.evidence_summary
                if summary:
                    st.write(f"Type: {summary.get('campaign_type')}")
                    st.write(f"Decision: {summary.get('next_cycle_action')} ({summary.get('target_status')})")
                    st.write(f"Evidence: {summary.get('evidence_status')}")
                    if summary.get("primary_kpis"):
                        st.dataframe(pd.DataFrame(summary["primary_kpis"]), hide_index=True, use_container_width=True)
            with col_out:
                st.markdown("**Output — narrative**")
                nar = ev.narrative
                if nar:
                    st.write(nar.get("target_assessment", ""))
                    if nar.get("strategic_lesson"):
                        st.caption(f"Lesson: {nar['strategic_lesson']}")
                    for item in nar.get("risks_and_confounders", []):
                        st.markdown(f"- _risk:_ {item}")
                    if nar.get("next_controlled_test"):
                        st.info(nar["next_controlled_test"])
            with col_verdict:
                st.markdown("**Verdict — checks**")
                for check in ev.consistency_checks:
                    st.markdown(f"{CHECK_ICON[check.passed]} `{check.name}` ({check.severity})")
                    st.caption(check.detail)
                for score in ev.criterion_scores:
                    st.markdown(f"⭐ `{score.name}`: {score.score}/5")
                    st.caption(score.rationale)


def main() -> None:
    _configure_page()
    _sidebar()
    st.title("Narrative quality evaluation")
    history = load_history()
    if not history:
        st.info("No evaluation runs yet. Use **Run new evaluation** in the sidebar to create the first one.")
        st.stop()
    tab_history, tab_detail = st.tabs(["History", "Run detail"])
    with tab_history:
        _history_view(history)
    with tab_detail:
        _run_detail_view(history)


if __name__ == "__main__":
    main()
