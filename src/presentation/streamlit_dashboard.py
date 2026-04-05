"""Streamlit-specific presentation helpers."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from ..core import MarketingExpertError
from ..ingestion import CampaignDataService
from ..logging.logger import logger
from ..pipelines import MarketingPipelineResult

PAGE_STYLE = """
<style>
    .stButton > button {
        width: 100%;
        height: 115px;
        font-size: 21px !important;
        font-weight: 800 !important;
        line-height: 1.35;
        border-radius: 10px;
        background-color: #f0f2f6;
        border: 1px solid #d1d5db;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #e5e7eb;
        border-color: #9ca3af;
        transform: translateY(-2px);
        box_shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .main-header {
        font-size: 3rem;
        color: #1f2937;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #4b5563;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
"""

CATEGORY_BUTTONS: tuple[tuple[str, str], ...] = (
    ("Customer Acquisition", "Customer Acquisition\nAnalyze your acquisition sources and costs"),
    ("Customer Satisfaction", "Customer Satisfaction\nMonitor customer sentiment and engagement"),
    ("Revenue Growth", "Revenue Growth\nTrack revenue trends and performance"),
    ("Customer Retention", "Customer Retention\nEvaluate churn and retention rates"),
)


def apply_page_style() -> None:
    """Apply page metadata and the shared Streamlit theme."""

    st.set_page_config(page_title="Marketing Expert Chatbot", page_icon="chart_with_upwards_trend", layout="wide")
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)


def render_header() -> None:
    """Render the app header."""

    st.markdown('<h1 class="main-header">Marketing Expert Chatbot</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Select a category below to analyze your marketing performance</p>',
        unsafe_allow_html=True,
    )


def render_sidebar(data_service: CampaignDataService) -> None:
    """Render the debug sidebar."""

    with st.sidebar:
        st.header("Debug Info")
        if st.checkbox("Show Raw Data"):
            try:
                st.dataframe(data_service.load_dataframe())
            except MarketingExpertError as exc:
                logger.error("Failed to load raw data for sidebar: {}", exc)
                st.error(str(exc))


def initialize_session_state() -> None:
    """Ensure expected session state keys exist."""

    if "selected_category" not in st.session_state:
        st.session_state.selected_category = ""
    if "run_analysis" not in st.session_state:
        st.session_state.run_analysis = False


def render_category_selector(on_select: Callable[[str], None]) -> None:
    """Render the category selection grid."""

    st.subheader("Choose a Category to Analyze")
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    columns = (col1, col2, col3, col4)

    for column, (category_name, button_label) in zip(columns, CATEGORY_BUTTONS):
        with column:
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            if st.button(button_label, use_container_width=True):
                on_select(category_name)

    st.markdown("---")


def render_analysis_result(result: MarketingPipelineResult) -> None:
    """Render a completed analysis result."""

    metrics_overall = result.metrics.overall
    report_payload = result.report.to_response_dict()

    st.caption(f"Run ID: `{result.correlation_id}`")
    render_overall_metric_cards(metrics_overall)
    st.markdown("<br>", unsafe_allow_html=True)
    render_validation_warnings(result.input_validation.warnings)
    render_analysis_summary(report_payload.get("analysis", {}))
    render_recommendations(report_payload.get("recommendations", []))


def format_currency(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"${value:,.0f}"
    return str(value)


def render_overall_metric_cards(metrics_overall: dict[str, object]) -> None:
    new_customers = metrics_overall.get(
        "Total New Customers",
        metrics_overall.get("Total Conversions", 0),
    )

    ui_cards = [
        ("Campaign Name", metrics_overall.get("Campaign Name", "Unknown")),
        ("Total New Customers", str(new_customers)),
        ("Total Revenue", format_currency(metrics_overall.get("Total Revenue", 0))),
        ("Total Spend", format_currency(metrics_overall.get("Total Spend", 0))),
    ]

    st.markdown("### Key Metrics")
    columns = st.columns(4)
    for index, (label, value) in enumerate(ui_cards):
        with columns[index]:
            st.markdown(
                f"""
                <div style="
                    background-color: white;
                    padding: 18px;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.10);
                    border: 2px solid #6366f1;
                    text-align: center;
                    height: 100%;
                ">
                    <span style="display:block; font-size:1.1em; font-weight:400; color:#4338ca; margin-bottom:6px; letter-spacing:0.03em;">{label}</span>
                    <span style="display:block; font-size:2.1em; font-weight:400; color:#111827;">{value}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_analysis_summary(analysis: dict[str, object]) -> None:
    st.markdown("### Analysis Summary")
    st.markdown(str(analysis.get("analysis", "")))

    root_cause = analysis.get("root_cause_hypothesis", "")
    if root_cause:
        st.info(f"**Root-cause hypothesis:** {root_cause}")

    signals = analysis.get("key_signals", [])
    if signals:
        with st.expander("Key Signals"):
            for signal in signals:
                st.write(f"- {signal}")

    issues = analysis.get("detected_issues", [])
    if issues:
        with st.expander("Detected Issues"):
            for issue in issues:
                st.write(f"- {issue}")

    risks = analysis.get("business_risks", [])
    if risks:
        with st.expander("Business Risks"):
            for risk in risks:
                st.write(f"- {risk}")

    confidence = analysis.get("confidence_score", 0)
    if isinstance(confidence, str):
        try:
            confidence = float(confidence.strip("%"))
        except ValueError:
            confidence = 0

    confidence = max(0, min(100, int(float(confidence))))
    st.progress(confidence / 100, text=f"Confidence Score: {confidence}%")


def render_validation_warnings(warnings: tuple[object, ...]) -> None:
    if not warnings:
        return

    with st.expander("Input Validation Warnings"):
        for warning in warnings:
            message = getattr(warning, "message", str(warning))
            field_name = getattr(warning, "field_name", None)
            code = getattr(warning, "code", "warning")
            if field_name:
                st.write(f"- {code} [{field_name}]: {message}")
            else:
                st.write(f"- {code}: {message}")


def render_recommendations(recommendations: list[dict[str, object]]) -> None:
    st.markdown("---")
    st.markdown("### Recommendations")

    priority_colors = {
        "high": "#dc2626",
        "medium": "#d97706",
        "low": "#16a34a",
    }

    for index, recommendation in enumerate(recommendations, start=1):
        priority = str(recommendation.get("priority", "medium")).lower()
        color = priority_colors.get(priority, "#6366f1")

        st.markdown(
            f"""
            <div style="
                background: #fff;
                border-left: 5px solid {color};
                border-radius: 10px;
                padding: 20px 24px;
                margin-bottom: 18px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:1.25em; font-weight:700; color:#1e293b;">{index}. {recommendation.get('title', '')}</span>
                    <span style="
                        background:{color}22;
                        color:{color};
                        font-weight:700;
                        padding:3px 12px;
                        border-radius:20px;
                        font-size:0.85em;
                    ">{priority.upper()} priority</span>
                </div>
                <div style="color:#475569; font-size:0.95em; margin-bottom:6px;">
                    <b>Effort:</b> {recommendation.get('effort', '')}
                    <b>Impact in:</b> {recommendation.get('time_to_see_impact', '')}
                    <b>Confidence:</b> {recommendation.get('confidence', '')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(f"**What's happening:** {recommendation.get('whats_happening', '')}")

        evidence = recommendation.get("evidence", [])
        if evidence:
            with st.expander("Evidence"):
                for item in evidence:
                    st.write(f"- {item}")

        actions = recommendation.get("what_you_should_do", [])
        if actions:
            with st.expander("Action Steps"):
                for step in actions:
                    if isinstance(step, dict):
                        st.markdown(f"**{step.get('step', '')}**")
                        st.write(f"Where: {step.get('where', '')}")
                        st.write(f"How: {step.get('how', '')}")
                        guardrails = step.get("guardrails", [])
                        if guardrails:
                            st.write("Guardrails: " + ", ".join(guardrails))
                    else:
                        st.write(f"- {step}")

        why_this_matters = recommendation.get("why_this_matters", "")
        if why_this_matters:
            st.markdown(f"**Why this matters:** {why_this_matters}")

        expected_impact = recommendation.get("expected_impact", {})
        if isinstance(expected_impact, dict) and expected_impact:
            st.markdown(
                f"**Expected impact:** {expected_impact.get('primary_kpi', '')} "
                f"to {expected_impact.get('direction', '')} - {expected_impact.get('explanation', '')}"
            )

        dependency_or_risk = recommendation.get("dependency_or_risk", [])
        if dependency_or_risk:
            with st.expander("Risks and Dependencies"):
                for item in dependency_or_risk:
                    st.write(f"- {item}")

        measurement_plan = recommendation.get("measurement_plan", {})
        if isinstance(measurement_plan, dict) and measurement_plan:
            with st.expander("Measurement Plan"):
                st.write(f"How to measure: {measurement_plan.get('how_to_measure', '')}")
                st.write(f"Success criteria: {measurement_plan.get('success_criteria', '')}")
                st.write(f"Check timing: {measurement_plan.get('check_timing', '')}")
                notes = measurement_plan.get("notes", "")
                if notes:
                    st.write(f"Notes: {notes}")

        st.markdown(f"*Owner suggestion: {recommendation.get('owner_suggestion', '')}*")
        st.markdown("---")
