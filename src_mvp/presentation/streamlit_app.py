"""Business-facing Streamlit report for the objective-led MVP pipeline."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src_mvp.config import load_budget_policy, load_objectives
from src_mvp.contracts import RecommendationReport
from src_mvp.paths import ARTIFACT_DIR, INPUT_DIR
from src_mvp.pipeline import MVPResult, run_mvp
from src_mvp.recommendation import run_recommendation

load_dotenv(ROOT / ".env")

OBJECTIVE_LABELS = {
    "OUTCOME_AWARENESS": "Awareness",
    "OUTCOME_ENGAGEMENT": "Engagement",
    "OUTCOME_LEADS": "Leads",
    "OUTCOME_SALES": "Sales",
}
ACTION_LABELS = {
    "scale": "Scale",
    "keep_as_test": "Hold / Test",
    "do_not_fund": "Do Not Fund",
    "insufficient_evidence": "Insufficient Evidence",
}
ACTION_COLORS = {
    "Scale": "#16815d",
    "Hold / Test": "#d68c16",
    "Do Not Fund": "#c44536",
    "Insufficient Evidence": "#6b7280",
}
OBJECTIVE_COLORS = {
    "Awareness": "#3978a8",
    "Engagement": "#7b61a8",
    "Leads": "#d17b32",
    "Sales": "#16815d",
}
METRIC_LABELS = {
    "link_ctr": "Link CTR",
    "cpm": "CPM",
    "cpc": "CPC",
    "order_creation_rate": "Order Creation Rate",
    "cost_per_created_order": "Cost per Created Order",
    "customer_delivered_rate": "Customer Delivered Rate",
    "net_roas": "Net ROAS",
}
BENCHMARK_SCOPE_LABELS = {
    "same_objective": "Same objective",
    "shared_primary_kpi_group": "Shared upper-funnel Link CTR",
    "unavailable": "Unavailable",
}
SIGNAL_LABELS = {
    "semantic_coverage_rate": "Conversation coverage",
    "high_purchase_intent_rate": "High purchase intent",
    "price_blocking_rate": "Price was blocking",
    "barrier_resolution_rate": "Barriers resolved",
    "agent_helpful_rate": "Agent helpful",
    "next_step_agreement_rate": "Next step agreed",
    "next_step_order_progression_rate": "Agreed step reached an order",
}


def _objective_label(value: object) -> str:
    return OBJECTIVE_LABELS.get(str(value), str(value).replace("OUTCOME_", "").title())


def _action_label(value: object) -> str:
    return ACTION_LABELS.get(str(value), str(value).replace("_", " ").title())


def _metric_label(value: object) -> str:
    return METRIC_LABELS.get(str(value), str(value).replace("_", " ").title())


def _benchmark_scope_label(value: object) -> str:
    return BENCHMARK_SCOPE_LABELS.get(
        str(value), str(value).replace("_", " ").title()
    )


def _numeric(value: object):
    result = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(result) else float(result)


def _number(value: object, digits: int = 0) -> str:
    numeric = _numeric(value)
    return "Not available" if numeric is None else f"{numeric:,.{digits}f}"


def _percent(value: object, digits: int = 1) -> str:
    numeric = _numeric(value)
    return "Not available" if numeric is None else f"{numeric:.{digits}%}"


def _money(value: object, currency: str, digits: int = 0) -> str:
    numeric = _numeric(value)
    return "Not available" if numeric is None else f"{currency} {numeric:,.{digits}f}"


def _metric_value(value: object, metric: str, currency: str) -> str:
    numeric = _numeric(value)
    if numeric is None:
        return "Not available"
    if metric in {"link_ctr", "order_creation_rate", "customer_delivered_rate"}:
        return f"{numeric:.1%}"
    if metric == "net_roas":
        return f"{numeric:.2f}x"
    return f"{currency} {numeric:,.2f}"


@st.cache_resource(show_spinner=False)
def _load_result(
    input_directory: str, signals_path: str, budget: float, currency: str
) -> MVPResult:
    """Build the report with the v2 semantic score and exploration policy."""
    policy = load_budget_policy().model_copy(
        update={"budget_units": float(budget), "currency": currency.strip() or "units"}
    )
    return run_mvp(
        input_directory=Path(input_directory).expanduser(),
        signals_path=Path(signals_path).expanduser(),
        policy=policy,
    )


def _configure_page() -> None:
    st.set_page_config(
        page_title="Objective-Led Campaign Review",
        page_icon=":material/query_stats:",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        :root { --ink:#17191c; --muted:#626973; --rule:#d9dde2; --soft:#f5f7f9; --blue:#3978a8; }
        .stApp { background:#fff; color:var(--ink); }
        [data-testid="stHeader"] { background:rgba(255,255,255,.96); }
        [data-testid="stMetric"] { border:1px solid var(--rule); border-radius:6px; padding:12px 14px; min-height:106px; }
        [data-testid="stMetricLabel"] { color:var(--muted); }
        [data-testid="stMetricValue"] { font-size:1.5rem; }
        .report-kicker { color:var(--blue); font-size:.78rem; font-weight:700; text-transform:uppercase; }
        .report-title { font-size:2rem; font-weight:720; line-height:1.2; margin:.15rem 0 .25rem; }
        .report-meta { color:var(--muted); font-size:.9rem; }
        .evidence-strip { border-left:4px solid var(--blue); background:#f2f7fb; padding:12px 15px; margin:16px 0 12px; }
        .decision-strip { border-left:4px solid #d68c16; background:#fff8eb; padding:12px 15px; margin:8px 0 14px; }
        .definition { background:var(--soft); border-top:1px solid var(--rule); border-bottom:1px solid var(--rule); padding:11px 14px; margin:8px 0 16px; }
        div[data-testid="stDataFrame"] { border:1px solid var(--rule); }
        button[kind="primary"] { border-radius:6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar() -> Tuple[str, str, float, str]:
    base_policy = load_budget_policy()
    with st.sidebar:
        st.header("Cycle settings")
        budget = st.number_input(
            "Next-cycle budget",
            min_value=1.0,
            value=float(base_policy.budget_units),
            step=100.0,
        )
        currency = st.text_input("Currency or unit", value=base_policy.currency)
        st.caption(
            "Each objective keeps its previous-cycle spend envelope. Campaigns share the "
            "full envelope using primary probability x conversation-quality lower bound."
        )
        with st.expander("Data sources"):
            input_directory = st.text_input("Sample 2 directory", value=str(INPUT_DIR))
            signals_path = st.text_input(
                "Conversation signals",
                value=os.getenv(
                    "MVP_CONVERSATION_SIGNALS_PATH",
                    str(ARTIFACT_DIR / "conversation_signals_v3_paid.jsonl"),
                ),
                key="mvp_conversation_signals_v3_path",
                help="The MVP requires signal_schema_version 3 or later.",
            )
        if st.button("Reload cycle", icon=":material/refresh:", width="stretch"):
            _load_result.clear()
            st.session_state.pop("mvp_llm_report", None)
            st.rerun()
        st.divider()
        st.subheader("Decision policy")
        st.markdown(
            "**Scale:** lower lift bound is above zero  \n"
            "**Hold / Test:** lift range crosses zero  \n"
            "**Do Not Fund:** upper lift bound is below zero"
        )
        st.caption(
            "Efficiency influences the action label. Conversation quality remains a separate "
            "score and contributes its lower uncertainty bound to budget priority."
        )
        st.divider()
        st.subheader("Business glossary")
        with st.expander("Primary KPI and efficiency"):
            st.markdown(
                "The **primary KPI** measures objective achievement. The **efficiency metric** checks what that outcome cost or returned."
            )
        with st.expander("Corrected score and range"):
            st.markdown(
                "The **corrected score** combines campaign and peer evidence. The **range** shows uncertainty around that estimate."
            )
        with st.expander("ROAS, CPM and CPC"):
            st.markdown(
                "**ROAS** is net revenue divided by spend. **CPM** is cost per 1,000 impressions. **CPC** is cost per link click."
            )
    return input_directory, signals_path, float(budget), currency.strip() or "units"


def _header(result: MVPResult) -> None:
    cycle = result.recommendation_input.cycle
    scope = result.recommendation_input.data_scope
    st.markdown('<div class="report-kicker">Completed-cycle evidence</div>', unsafe_allow_html=True)
    st.markdown('<div class="report-title">Objective-Led Campaign Review</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="report-meta">{cycle.start_date or "Unknown start"} to '
        f'{cycle.end_date or "Unknown end"} &nbsp;|&nbsp; {cycle.cycle_id}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="evidence-strip"><b>MVP evidence assumption:</b> '
        f'{scope.paid_attributed_conversations:,} paid-attributed conversations are treated as '
        f'the complete business-outcome dataset. Conversation semantics cover '
        f'{scope.semantic_conversations:,} conversations ({_percent(scope.semantic_coverage_rate)}).</div>',
        unsafe_allow_html=True,
    )


def _allocation_frame(result: MVPResult) -> pd.DataFrame:
    frame = pd.DataFrame([item.model_dump(mode="json") for item in result.allocations])
    frame["Objective"] = frame["objective"].map(_objective_label)
    frame["Action"] = frame["action"].map(_action_label)
    frame["Pool"] = frame["budget_pool"].str.replace("_", " ").str.title()
    return frame


def _campaign_table(frame: pd.DataFrame) -> pd.DataFrame:
    shown = frame.copy()
    shown["Objective"] = shown["objective"].map(_objective_label)
    shown["Primary KPI"] = shown["score_metric"].map(_metric_label)
    shown["Action"] = shown["recommended_action"].map(_action_label)
    shown["Conversation quality"] = shown["semantic_score"].map(lambda s: s["corrected_rate"])
    shown["Quality status"] = shown["semantic_score"].map(lambda s: s["status"])
    shown["Benchmark source"] = shown["benchmark_scope"].map(
        _benchmark_scope_label
    )
    return shown[
        [
            "campaign_name", "Objective", "Primary KPI", "score_successes",
            "score_trials", "raw_rate", "corrected_rate", "range_low",
            "range_high", "Benchmark source", "benchmark_quality",
            "portfolio_context_benchmark", "probability_better", "efficiency_value",
            "efficiency_comparison", "Conversation quality", "Quality status", "Action", "recommended_budget_units",
        ]
    ].rename(
        columns={
            "campaign_name": "Campaign", "score_successes": "Successes",
            "score_trials": "Trials", "raw_rate": "Raw",
            "corrected_rate": "Corrected", "range_low": "Range low",
            "range_high": "Range high", "probability_better": "Probability better",
            "benchmark_quality": "Benchmark quality",
            "portfolio_context_benchmark": "Portfolio context",
            "efficiency_value": "Efficiency", "efficiency_comparison": "Efficiency vs peer",
            "recommended_budget_units": "Recommended budget",
        }
    )


PERCENT_COLUMNS = {
    "Conversation quality": st.column_config.NumberColumn(format="percent"),
    "Raw": st.column_config.NumberColumn(format="percent"),
    "Corrected": st.column_config.NumberColumn(format="percent"),
    "Range low": st.column_config.NumberColumn(format="percent"),
    "Range high": st.column_config.NumberColumn(format="percent"),
    "Probability better": st.column_config.NumberColumn(format="percent"),
    "Portfolio context": st.column_config.NumberColumn(format="percent"),
}


def _portfolio_view(result: MVPResult, currency: str) -> None:
    campaigns = result.scorecards["campaign"].copy()
    allocations = _allocation_frame(result)
    campaigns = campaigns.merge(
        allocations[["campaign_id", "recommended_budget_units"]],
        on="campaign_id",
        how="left",
    )
    allocated = float(allocations["recommended_budget_units"].sum())
    unallocated = float(result.recommendation_input.unallocated_budget_units)
    actions = Counter(campaigns["recommended_action"])
    columns = st.columns(5)
    columns[0].metric("Previous media spend", _money(campaigns["spend"].sum(), currency))
    columns[1].metric("Observed net revenue", _money(campaigns["net_revenue"].sum(), currency))
    columns[2].metric("Delivered orders", f"{int(campaigns['delivered_orders'].sum()):,}")
    columns[3].metric("Next budget allocated", _money(allocated, currency))
    columns[4].metric("Next budget unallocated", _money(unallocated, currency))

    left, right = st.columns([1.65, 1])
    with left:
        st.subheader("Campaign evidence ranges")
        chart_data = campaigns.dropna(subset=["range_low", "range_high"]).copy()
        chart_data["Objective"] = chart_data["objective"].map(_objective_label)
        chart_data["Action"] = chart_data["recommended_action"].map(_action_label)
        if chart_data.empty:
            st.info("No campaigns have enough comparable evidence for corrected ranges.")
        else:
            intervals = alt.Chart(chart_data).mark_rule(strokeWidth=4).encode(
                x=alt.X("range_low:Q", title="Primary KPI", axis=alt.Axis(format=".0%")),
                x2="range_high:Q",
                y=alt.Y("campaign_name:N", title=None, sort="-x"),
                color=alt.Color(
                    "Objective:N",
                    scale=alt.Scale(domain=list(OBJECTIVE_COLORS), range=list(OBJECTIVE_COLORS.values())),
                ),
                tooltip=[
                    alt.Tooltip("campaign_name:N", title="Campaign"), "Objective:N",
                    alt.Tooltip("raw_rate:Q", title="Raw", format=".2%"),
                    alt.Tooltip("corrected_rate:Q", title="Corrected", format=".2%"),
                    alt.Tooltip("benchmark:Q", title="Benchmark", format=".2%"),
                    alt.Tooltip("range_low:Q", title="Range low", format=".2%"),
                    alt.Tooltip("range_high:Q", title="Range high", format=".2%"), "Action:N",
                ],
            )
            points = alt.Chart(chart_data).mark_point(
                filled=True, color="#17191c", size=75
            ).encode(x="corrected_rate:Q", y=alt.Y("campaign_name:N", sort="-x"))
            st.altair_chart((intervals + points).properties(height=390), use_container_width=True)
            st.caption("Compare ranges only within the same objective; objectives use different success definitions.")
    with right:
        st.subheader("Next-cycle actions")
        action_data = pd.DataFrame(
            {"Action": [_action_label(key) for key in actions], "Campaigns": list(actions.values())}
        )
        chart = alt.Chart(action_data).mark_bar(cornerRadiusEnd=3).encode(
            y=alt.Y("Action:N", title=None, sort="-x"),
            x=alt.X("Campaigns:Q", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color(
                "Action:N",
                scale=alt.Scale(domain=list(ACTION_COLORS), range=list(ACTION_COLORS.values())),
                legend=None,
            ),
            tooltip=["Action:N", "Campaigns:Q"],
        ).properties(height=210)
        st.altair_chart(chart, use_container_width=True)
        st.markdown(
            f'<div class="decision-strip"><b>Current portfolio:</b> '
            f'{actions.get("scale", 0)} Scale, {actions.get("keep_as_test", 0)} Hold / Test, '
            f'{actions.get("do_not_fund", 0)} Do Not Fund, and '
            f'{actions.get("insufficient_evidence", 0)} Insufficient Evidence.</div>',
            unsafe_allow_html=True,
        )
    st.subheader("Campaign portfolio")
    st.dataframe(
        _campaign_table(campaigns), width="stretch", hide_index=True,
        column_config={**PERCENT_COLUMNS, "Recommended budget": st.column_config.NumberColumn(format="%.2f")},
    )


def _objective_view(result: MVPResult, currency: str) -> None:
    registry = load_objectives()
    campaigns = result.scorecards["campaign"]
    rows: List[Dict[str, object]] = []
    for objective, contract in registry.objectives.items():
        subset = campaigns[campaigns["objective"].eq(objective)]
        rows.append(
            {
                "Objective": _objective_label(objective),
                "Business purpose": contract.business_job,
                "Business question": contract.success_question,
                "Primary KPI": _metric_label(contract.primary_metric),
                "Primary calculation": f"{contract.primary_numerator.replace('_', ' ')} / {contract.primary_denominator.replace('_', ' ')}",
                "Efficiency gate": _metric_label(contract.efficiency_metric),
                "Preferred direction": f"Higher {_metric_label(contract.primary_metric)}; {contract.efficiency_direction.title()} {_metric_label(contract.efficiency_metric)}",
                "Campaigns": len(subset),
                "Previous spend": float(subset["spend"].sum()),
            }
        )
    st.subheader("Objective measurement map")
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.markdown(
        '<div class="definition"><b>Reading rule:</b> the objective defines success; '
        'the primary KPI measures it; the efficiency gate checks whether the result was economically acceptable.</div>',
        unsafe_allow_html=True,
    )
    selected = st.selectbox("Objective detail", list(registry.objectives), format_func=_objective_label)
    contract = registry.objectives[selected]
    subset = campaigns[campaigns["objective"].eq(selected)].copy()
    columns = st.columns(4)
    columns[0].metric("Campaigns", f"{len(subset):,}")
    columns[1].metric("Primary KPI", _metric_label(contract.primary_metric))
    columns[2].metric("Efficiency gate", _metric_label(contract.efficiency_metric))
    columns[3].metric("Previous spend", _money(subset["spend"].sum(), currency))
    st.markdown(f"**Business question:** {contract.success_question}")
    if subset["benchmark_quality"].eq("provisional").any():
        st.info(
            "Same-objective peers are insufficient. Corrected Link CTR uses the shared "
            "Awareness and Engagement fallback, is marked provisional, and can fund only a test."
        )
    chart_data = subset.dropna(subset=["range_low", "range_high"])
    if chart_data.empty:
        st.info("This objective lacks enough same-objective peers to build corrected ranges.")
    else:
        intervals = alt.Chart(chart_data).mark_rule(
            strokeWidth=5, color=OBJECTIVE_COLORS[_objective_label(selected)]
        ).encode(
            x=alt.X("range_low:Q", title=_metric_label(contract.primary_metric), axis=alt.Axis(format=".0%")),
            x2="range_high:Q",
            y=alt.Y("campaign_name:N", title=None, sort="-x"),
            tooltip=[
                alt.Tooltip("campaign_name:N", title="Campaign"),
                alt.Tooltip("raw_rate:Q", title="Raw", format=".2%"),
                alt.Tooltip("corrected_rate:Q", title="Corrected", format=".2%"),
                alt.Tooltip("benchmark:Q", title="Benchmark", format=".2%"),
            ],
        )
        points = alt.Chart(chart_data).mark_point(
            filled=True, color="#17191c", size=90
        ).encode(x="corrected_rate:Q", y=alt.Y("campaign_name:N", sort="-x"))
        st.altair_chart(
            (intervals + points).properties(height=max(180, len(subset) * 55)),
            use_container_width=True,
        )


def _score_point_chart(row: pd.Series) -> alt.Chart:
    values = pd.DataFrame(
        {
            "Estimate": ["Raw result", "Corrected score", "Peer benchmark"],
            "Value": [row.get("raw_rate"), row.get("corrected_rate"), row.get("benchmark")],
        }
    ).dropna()
    points = alt.Chart(values).mark_point(filled=True, size=145).encode(
        x=alt.X("Value:Q", axis=alt.Axis(format=".0%"), title="Primary KPI"),
        y=alt.Y("Estimate:N", title=None),
        color=alt.Color(
            "Estimate:N",
            scale=alt.Scale(
                domain=["Raw result", "Corrected score", "Peer benchmark"],
                range=["#3978a8", "#16815d", "#d68c16"],
            ),
            legend=None,
        ),
        tooltip=["Estimate:N", alt.Tooltip("Value:Q", format=".2%")],
    )
    if pd.isna(row.get("range_low")) or pd.isna(row.get("range_high")):
        return points.properties(height=170)
    interval = pd.DataFrame(
        {"Estimate": ["Corrected score"], "Low": [row["range_low"]], "High": [row["range_high"]]}
    )
    rule = alt.Chart(interval).mark_rule(strokeWidth=5, color="#16815d").encode(
        x="Low:Q", x2="High:Q", y="Estimate:N"
    )
    return (rule + points).properties(height=170)


def _signal_chart(row: pd.Series) -> alt.Chart:
    data = pd.DataFrame(
        [{"Signal": label, "Rate": row.get(column)} for column, label in SIGNAL_LABELS.items()]
    ).dropna()
    return alt.Chart(data).mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y("Signal:N", title=None, sort="-x"),
        x=alt.X("Rate:Q", axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1])),
        color=alt.condition(
            alt.datum.Signal == "Price was blocking", alt.value("#c44536"), alt.value("#3978a8")
        ),
        tooltip=["Signal:N", alt.Tooltip("Rate:Q", format=".1%")],
    ).properties(height=275)


def _entity_table(frame: pd.DataFrame) -> pd.DataFrame:
    shown = frame.copy()
    shown["Action"] = shown["recommended_action"].map(_action_label)
    shown["Conversation quality"] = shown["semantic_score"].map(lambda s: s["corrected_rate"])
    shown["Quality status"] = shown["semantic_score"].map(lambda s: s["status"])
    shown["Primary KPI"] = shown["score_metric"].map(_metric_label)
    shown["Benchmark source"] = shown["benchmark_scope"].map(
        _benchmark_scope_label
    )
    return shown[
        [
            "entity_name", "campaign_name", "Primary KPI", "score_successes",
            "score_trials", "raw_rate", "corrected_rate", "range_low",
            "range_high", "Benchmark source", "portfolio_context_benchmark",
            "probability_better", "efficiency_value",
            "efficiency_comparison", "Conversation quality", "Quality status", "spend", "Action",
        ]
    ].rename(
        columns={
            "entity_name": "Entity", "campaign_name": "Campaign",
            "score_successes": "Successes", "score_trials": "Trials",
            "raw_rate": "Raw", "corrected_rate": "Corrected",
            "range_low": "Range low", "range_high": "Range high",
            "probability_better": "Probability better", "efficiency_value": "Efficiency",
            "portfolio_context_benchmark": "Portfolio context",
            "efficiency_comparison": "Efficiency vs peer", "spend": "Previous spend",
        }
    )


def _semantic_table(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([
        {"Campaign": row["campaign_name"], "Entity": row["entity_name"],
         "Quality metric": row["semantic_score"]["metric"],
         **{key: row["semantic_score"][key] for key in (
             "eligible_customers", "successes", "trials", "unknown_customers",
             "missing_customers", "raw_rate", "corrected_rate", "range_low", "range_high",
             "prior_source", "peer_count", "probability_better", "status"
         )}}
        for _, row in frame.iterrows()
    ])


def _show_semantic_table(frame: pd.DataFrame) -> None:
    st.subheader("Conversation quality evidence")
    st.dataframe(_semantic_table(frame), hide_index=True, width="stretch",
                 column_config={key: st.column_config.NumberColumn(format="percent") for key in (
                     "raw_rate", "corrected_rate", "range_low", "range_high", "probability_better"
                 )})


def _campaign_view(result: MVPResult, currency: str) -> None:
    campaigns = result.scorecards["campaign"]
    allocations = _allocation_frame(result)
    campaign_name = st.selectbox("Campaign", campaigns["campaign_name"].tolist())
    row = campaigns[campaigns["campaign_name"].eq(campaign_name)].iloc[0]
    allocation = allocations[allocations["campaign_id"].eq(row["campaign_id"])].iloc[0]
    st.markdown(
        f'<div class="decision-strip"><b>{_action_label(row["recommended_action"])}</b> '
        f'for the next cycle &nbsp;|&nbsp; {_objective_label(row["objective"])} objective '
        f'&nbsp;|&nbsp; Recommended budget: {_money(allocation["recommended_budget_units"], currency)}</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(6)
    columns[0].metric("Raw result", _percent(row["raw_rate"]))
    columns[1].metric("Corrected score", _percent(row["corrected_rate"]))
    columns[2].metric("Peer benchmark", _percent(row["benchmark"]))
    columns[3].metric("Probability better", _percent(row["probability_better"]))
    columns[4].metric("Evidence", str(row["evidence_status"]).title())
    columns[5].metric(
        "Benchmark source", _benchmark_scope_label(row["benchmark_scope"])
    )
    if row["benchmark_quality"] == "provisional":
        st.info(
            "This corrected score uses the shared Awareness and Engagement Link CTR "
            "fallback. It is provisional, so the final action is capped at Hold / Test. "
            f"The whole-portfolio context is {_percent(row['portfolio_context_benchmark'])} "
            "and does not affect the decision."
        )

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Primary KPI evidence")
        st.altair_chart(_score_point_chart(row), use_container_width=True)
        st.markdown(
            f"**Observed evidence:** {_number(row['score_successes'])} successes from "
            f"{_number(row['score_trials'])} trials.  "
            f"**Expected range:** {_percent(row['range_low'])} to {_percent(row['range_high'])}."
        )
        if pd.notna(row.get("lift_low")):
            lift_data = pd.DataFrame(
                {
                    "Campaign": [campaign_name], "Low": [row["lift_low"]],
                    "Expected": [row["expected_lift"]], "High": [row["lift_high"]],
                }
            )
            rule = alt.Chart(lift_data).mark_rule(strokeWidth=6, color="#d68c16").encode(
                x=alt.X("Low:Q", axis=alt.Axis(format="+.0%"), title="Favorable lift versus benchmark"),
                x2="High:Q", y=alt.value(35),
                tooltip=[
                    alt.Tooltip("Low:Q", format="+.2%"),
                    alt.Tooltip("Expected:Q", format="+.2%"),
                    alt.Tooltip("High:Q", format="+.2%"),
                ],
            )
            point = alt.Chart(lift_data).mark_point(
                filled=True, size=100, color="#17191c"
            ).encode(x="Expected:Q", y=alt.value(35))
            zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
                color="#626973", strokeDash=[5, 4]
            ).encode(x="zero:Q")
            st.altair_chart(
                (rule + point + zero).properties(height=95),
                use_container_width=True,
            )
    with right:
        st.subheader("Efficiency gate")
        metric = str(row["efficiency_metric"])
        efficiency_columns = st.columns(2)
        efficiency_columns[0].metric("Campaign", _metric_value(row["efficiency_value"], metric, currency))
        efficiency_columns[1].metric("Peer median", _metric_value(row["efficiency_benchmark"], metric, currency))
        st.markdown(
            f"**{_metric_label(metric)}:** {str(row['efficiency_comparison']).replace('_', ' ')}."
        )
        st.subheader("Business outcomes")
        outcomes = pd.DataFrame(
            {
                "Measure": [
                    "Previous spend", "Observed conversations", "Mature conversations",
                    "Unresolved conversations", "Created orders", "Delivered orders", "Net revenue",
                ],
                "Value": [
                    _money(row["spend"], currency), _number(row["observed_conversations"]),
                    _number(row["mature_conversations"]), _number(row["unresolved_conversations"]),
                    _number(row["mature_orders_created"]), _number(row["delivered_orders"]),
                    _money(row["net_revenue"], currency),
                ],
            }
        )
        st.dataframe(outcomes, hide_index=True, width="stretch")

    st.subheader("Customer conversation evidence")
    semantic = row["semantic_score"]
    st.markdown(f"**{semantic['metric'].replace('_', ' ').title()}:** {semantic['definition']}")
    quality_columns = st.columns(4)
    quality_columns[0].metric("Semantic evidence", f"{semantic['successes']} / {semantic['trials']}")
    quality_columns[1].metric("Raw quality", _percent(semantic["raw_rate"]))
    quality_columns[2].metric("Corrected quality", _percent(semantic["corrected_rate"]))
    quality_columns[3].metric("Quality status", semantic["status"].replace("_", " ").title())
    st.markdown(
        f"**95% quality range:** {_percent(semantic['range_low'])} to {_percent(semantic['range_high'])}. "
        f"**Unknown / missing customers:** {semantic['unknown_customers']} / {semantic['missing_customers']}. "
        f"**Prior:** {semantic['prior_source'].replace('_', ' ')}."
    )
    st.caption(
        "One earliest mature conversation per customer within this entity. Automated labels are "
        "unreviewed; the range captures sampling uncertainty conditional on their accuracy. "
        "Conversation quality can prioritize test budgets within the same objective."
    )
    signal_col, alignment_col = st.columns([1.4, 1])
    with signal_col:
        if int(row["semantic_conversations"]) == 0:
            st.info("No validated conversation signals are available for this campaign.")
        else:
            st.altair_chart(_signal_chart(row), use_container_width=True)
    with alignment_col:
        st.metric("Ad-message alignment", _percent(row["ad_alignment_rate"]))
        st.metric("Analyzed conversations", _number(row["semantic_conversations"]))
        st.markdown(f"**Leading customer need:** {row.get('top_customer_need') or 'Not established'}")
        st.markdown(f"**Leading barrier:** {row.get('top_barrier') or 'Not established'}")
        st.markdown(f"**Leading value driver:** {row.get('top_value_driver') or 'Not established'}")
        st.caption("These diagnostics suggest explanations. The explicit conversation-quality rule drives the separate semantic score.")

    st.subheader("Ad set, ad, creative and audience evidence")
    level = st.radio(
        "Detail level", ["adset", "ad", "creative", "audience"], horizontal=True,
        format_func=lambda value: {
            "adset": "Ad Sets", "ad": "Ads", "creative": "Creatives", "audience": "Audiences"
        }[value],
    )
    children = result.scorecards[level]
    children = children[children["campaign_id"].eq(row["campaign_id"])].copy()
    _show_semantic_table(children)
    st.dataframe(
        _entity_table(children), width="stretch", hide_index=True,
        column_config=PERCENT_COLUMNS,
    )
    if level in {"creative", "audience"}:
        st.caption("Creative and audience actions are diagnostic. The MVP allocates budget only at campaign level.")


def _entities_view(result: MVPResult) -> None:
    level = st.radio(
        "Scorecard level", ["adset", "ad", "creative", "audience"], horizontal=True,
        format_func=lambda value: {
            "adset": "Ad Sets", "ad": "Ads", "creative": "Creatives", "audience": "Audiences"
        }[value], key="entity_level",
    )
    frame = result.scorecards[level].copy()
    objectives = sorted(frame["objective"].dropna().unique())
    objective = st.selectbox(
        "Objective", ["ALL"] + objectives,
        format_func=lambda value: "All objectives" if value == "ALL" else _objective_label(value),
        key="entity_objective",
    )
    if objective != "ALL":
        frame = frame[frame["objective"].eq(objective)]
    campaigns = sorted(frame["campaign_name"].dropna().unique())
    campaign = st.selectbox("Campaign filter", ["ALL"] + campaigns, key="entity_campaign")
    if campaign != "ALL":
        frame = frame[frame["campaign_name"].eq(campaign)]
    _show_semantic_table(frame)
    chart_data = frame.dropna(subset=["lift_low", "lift_high"]).copy()
    chart_data["Action"] = chart_data["recommended_action"].map(_action_label)
    if chart_data.empty:
        st.info("The selected entities do not have sufficient peer evidence for lift ranges.")
    else:
        intervals = alt.Chart(chart_data).mark_rule(strokeWidth=5).encode(
            x=alt.X("lift_low:Q", title="Favorable lift versus same-objective peers", axis=alt.Axis(format="+.0%")),
            x2="lift_high:Q",
            y=alt.Y("entity_name:N", title=None, sort="-x"),
            color=alt.Color(
                "Action:N", scale=alt.Scale(domain=list(ACTION_COLORS), range=list(ACTION_COLORS.values()))
            ),
            tooltip=[
                alt.Tooltip("entity_name:N", title="Entity"),
                alt.Tooltip("campaign_name:N", title="Campaign"),
                alt.Tooltip("lift_low:Q", format="+.2%"),
                alt.Tooltip("expected_lift:Q", format="+.2%"),
                alt.Tooltip("lift_high:Q", format="+.2%"),
                alt.Tooltip("probability_better:Q", format=".2%"),
            ],
        )
        zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
            color="#17191c", strokeDash=[5, 4]
        ).encode(x="zero:Q")
        st.altair_chart(
            (intervals + zero).properties(height=max(240, min(720, len(chart_data) * 32))),
            use_container_width=True,
        )
    st.dataframe(
        _entity_table(frame), width="stretch", hide_index=True,
        column_config=PERCENT_COLUMNS,
    )


def _customer_view(result: MVPResult) -> None:
    _show_semantic_table(result.scorecards["campaign"])
    campaigns = result.scorecards["campaign"].copy()
    signal_columns = list(SIGNAL_LABELS)
    st.subheader("Conversation signals")
    st.markdown(
        '<div class="definition"><b>Business question:</b> what did customers want, '
        'what blocked them, and did the conversation progress?</div>',
        unsafe_allow_html=True,
    )
    melted = campaigns[["campaign_name", *signal_columns]].melt(
        "campaign_name", var_name="signal", value_name="rate"
    ).dropna()
    melted["Signal"] = melted["signal"].map(SIGNAL_LABELS)
    heatmap = alt.Chart(melted).mark_rect().encode(
        x=alt.X("Signal:N", title=None, axis=alt.Axis(labelAngle=-32)),
        y=alt.Y("campaign_name:N", title=None),
        color=alt.Color(
            "rate:Q", title="Rate",
            scale=alt.Scale(domain=[0, 0.5, 1], range=["#e9eef2", "#e2a44d", "#16815d"]),
            legend=alt.Legend(format=".0%", orient="top"),
        ),
        tooltip=[
            alt.Tooltip("campaign_name:N", title="Campaign"), "Signal:N",
            alt.Tooltip("rate:Q", format=".1%"),
        ],
    ).properties(height=390)
    st.altair_chart(heatmap, use_container_width=True)
    st.caption("Unknown or not-assessable labels are excluded from each signal denominator, rather than treated as negative.")

    st.subheader("Ad-message alignment")
    st.markdown(
        '<div class="definition"><b>Business question:</b> did the need expressed in '
        'WhatsApp match the product, offer, and promise in the ad?</div>',
        unsafe_allow_html=True,
    )
    alignment = campaigns.dropna(subset=["ad_alignment_rate"])
    alignment_chart = alt.Chart(alignment).mark_bar(
        cornerRadiusEnd=3, color="#3978a8"
    ).encode(
        y=alt.Y("campaign_name:N", title=None, sort="-x"),
        x=alt.X(
            "ad_alignment_rate:Q", title="Aligned conversations",
            axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1]),
        ),
        tooltip=[
            alt.Tooltip("campaign_name:N", title="Campaign"),
            alt.Tooltip("ad_alignment_rate:Q", title="Aligned", format=".1%"),
            alt.Tooltip("semantic_conversations:Q", title="Analyzed conversations"),
        ],
    ).properties(height=350)
    st.altair_chart(alignment_chart, use_container_width=True)
    themes = campaigns[
        [
            "campaign_name", "semantic_conversations", "semantic_coverage_rate",
            "top_customer_need", "top_barrier", "top_value_driver",
        ]
    ].rename(
        columns={
            "campaign_name": "Campaign", "semantic_conversations": "Analyzed conversations",
            "semantic_coverage_rate": "Coverage", "top_customer_need": "Leading customer need",
            "top_barrier": "Leading barrier", "top_value_driver": "Leading value driver",
        }
    )
    st.dataframe(
        themes, width="stretch", hide_index=True,
        column_config={"Coverage": st.column_config.NumberColumn(format="percent")},
    )


def _budget_plan(result: MVPResult) -> pd.DataFrame:
    campaigns = result.scorecards["campaign"]
    allocations = _allocation_frame(result)
    total_budget = float(result.recommendation_input.cycle.next_budget_amount)
    spend_by_objective = campaigns.groupby("objective")["spend"].sum()
    spend_total = float(spend_by_objective.sum())
    rows: List[Dict[str, object]] = []
    for objective, spend in spend_by_objective.items():
        share = float(spend / spend_total) if spend_total else 0.0
        subset = allocations[allocations["objective"].eq(objective)]
        allocated = float(subset["recommended_budget_units"].sum())
        envelope = total_budget * share
        rows.append(
            {
                "Objective": _objective_label(objective),
                "Previous spend share": share,
                "Objective envelope": envelope,
                "Score-based allocation": allocated,
                "Previous-spend scenario": float(
                    subset["previous_spend_budget_units"].sum()
                ),
                "Unallocated": max(envelope - allocated, 0.0),
            }
        )
    return pd.DataFrame(rows)


def _budget_view(result: MVPResult, currency: str) -> None:
    plan = _budget_plan(result)
    allocations = _allocation_frame(result)
    total = float(result.recommendation_input.cycle.next_budget_amount)
    allocated = float(allocations["recommended_budget_units"].sum())
    unallocated = float(result.recommendation_input.unallocated_budget_units)
    columns = st.columns(4)
    columns[0].metric("Next-cycle budget", _money(total, currency))
    columns[1].metric("Allocation method", "Two-factor score")
    columns[2].metric("Campaigns funded", _number((allocations["recommended_budget_units"] > 0).sum()))
    columns[3].metric("Currently unallocated", _money(unallocated, currency))

    chart_data = plan.melt(
        id_vars="Objective",
        value_vars=["Score-based allocation", "Unallocated"],
        var_name="Budget status", value_name="Budget",
    )
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("Objective:N", title=None),
        y=alt.Y("Budget:Q", title=f"Next-cycle budget ({currency})"),
        color=alt.Color(
            "Budget status:N",
            scale=alt.Scale(
                domain=["Score-based allocation", "Unallocated"],
                range=["#16815d", "#d9dde2"],
            ),
            legend=alt.Legend(orient="top"),
        ),
        tooltip=["Objective:N", "Budget status:N", alt.Tooltip("Budget:Q", format=",.2f")],
    ).properties(height=360)
    st.altair_chart(chart, use_container_width=True)
    st.caption(
        f"{_money(allocated, currency)} is allocated. A campaign needs both a primary "
        "probability and a conversation-quality lower bound to receive a score-based share."
    )

    st.subheader("Objective envelopes")
    st.dataframe(
        plan, width="stretch", hide_index=True,
        column_config={
            "Previous spend share": st.column_config.NumberColumn(format="percent"),
            "Objective envelope": st.column_config.NumberColumn(format="%.2f"),
            "Score-based allocation": st.column_config.NumberColumn(format="%.2f"),
            "Previous-spend scenario": st.column_config.NumberColumn(format="%.2f"),
            "Unallocated": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.subheader("Campaign allocations")
    st.caption(
        "Allocation priority = primary KPI probability better x conversation-quality lower "
        "bound. Priorities are normalized within each objective. Actions remain reporting "
        "labels and do not gate this POC budget."
    )
    shown = allocations[
        [
            "campaign_name", "Objective", "Action", "Pool", "allocation_weight",
            "recommended_budget_units", "recommended_budget_share",
            "primary_probability_component", "semantic_priority", "allocation_priority",
            "previous_spend_budget_units", "allocation_basis",
        ]
    ].rename(
        columns={
            "campaign_name": "Campaign", "allocation_weight": "Pool weight",
            "recommended_budget_units": "Recommended budget",
            "recommended_budget_share": "Portfolio share",
            "primary_probability_component": "Primary probability",
            "semantic_priority": "Quality lower bound",
            "allocation_priority": "Priority product",
            "previous_spend_budget_units": "Previous-spend scenario",
            "allocation_basis": "Allocation basis",
        }
    )
    st.dataframe(
        shown, width="stretch", hide_index=True,
        column_config={
            "Pool weight": st.column_config.NumberColumn(format="percent"),
            "Recommended budget": st.column_config.NumberColumn(format="%.2f"),
            "Portfolio share": st.column_config.NumberColumn(format="percent"),
            "Primary probability": st.column_config.NumberColumn(format="percent"),
            "Quality lower bound": st.column_config.NumberColumn(format="percent"),
            "Priority product": st.column_config.NumberColumn(format="%.4f"),
            "Previous-spend scenario": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    st.subheader("Named tests for Keep as Test campaigns")
    if not result.exploration_tests:
        st.info("No funded Keep as Test campaigns are present.")
    for test in result.exploration_tests:
        with st.expander(f"{test.campaign_name} | {_money(test.assigned_budget_units, currency, 2)}"):
            st.markdown(f"**Hypothesis:** {test.hypothesis}")
            st.markdown(f"**Primary KPI:** {_metric_label(test.primary_metric)}")
            st.markdown(f"**Success:** {test.success_rule}")
            st.markdown(f"**Failure:** {test.failure_rule}")
            st.markdown(f"**Stop:** {test.stop_rule}")


def _deterministic_recommendation(result: MVPResult, currency: str) -> None:
    campaigns = result.scorecards["campaign"]
    allocations = _allocation_frame(result)
    counts = Counter(campaigns["recommended_action"])
    allocated = float(allocations["recommended_budget_units"].sum())
    unallocated = float(result.recommendation_input.unallocated_budget_units)
    st.markdown(
        f"The cycle produces **{counts.get('scale', 0)} Scale**, "
        f"**{counts.get('keep_as_test', 0)} Hold / Test**, "
        f"**{counts.get('do_not_fund', 0)} Do Not Fund**, and "
        f"**{counts.get('insufficient_evidence', 0)} Insufficient Evidence** decisions. "
        f"The rules allocate **{_money(allocated, currency)}** and leave "
        f"**{_money(unallocated, currency)}** unallocated."
    )
    for _, row in campaigns.iterrows():
        allocation = allocations[allocations["campaign_id"].eq(row["campaign_id"])].iloc[0]
        with st.expander(f"{row['campaign_name']} | {_action_label(row['recommended_action'])}"):
            semantic = row["semantic_score"]
            st.markdown(
                f"**Conversation quality:** {semantic['successes']} / {semantic['trials']} "
                f"assessable customers; corrected {_percent(semantic['corrected_rate'])}; "
                f"95% range {_percent(semantic['range_low'])} to {_percent(semantic['range_high'])}. "
                f"**Budget allocation basis:** {allocation['allocation_basis'].replace('_', ' ')}. "
                f"Previous-spend scenario: {_money(allocation['previous_spend_budget_units'], currency, 2)}."
            )
            st.markdown(
                f"**Objective:** {_objective_label(row['objective'])}  \n"
                f"**Evidence:** {_number(row['score_successes'])} successes from {_number(row['score_trials'])} trials  \n"
                f"**Raw and corrected:** {_percent(row['raw_rate'])} and {_percent(row['corrected_rate'])}  \n"
                f"**Expected range:** {_percent(row['range_low'])} to {_percent(row['range_high'])}  \n"
                f"**Probability better:** {_percent(row['probability_better'])}  \n"
                f"**Benchmark:** {_benchmark_scope_label(row['benchmark_scope'])} "
                f"({str(row['benchmark_quality']).replace('_', ' ')})  \n"
                f"**Portfolio context only:** {_percent(row['portfolio_context_benchmark'])}  \n"
                f"**Efficiency:** {str(row['efficiency_comparison']).replace('_', ' ')}  \n"
                f"**Recommended budget:** {_money(allocation['recommended_budget_units'], currency, 2)}"
            )
            st.markdown(
                f"**Conversation evidence:** leading barrier is "
                f"{row.get('top_barrier') or 'not established'}; leading value driver is "
                f"{row.get('top_value_driver') or 'not established'}; ad-message alignment is "
                f"{_percent(row.get('ad_alignment_rate'))}."
            )


def _render_llm_report(report: RecommendationReport) -> None:
    st.subheader("Executive narrative")
    st.write(report.executive_summary)
    st.markdown(f"**Budget summary:** {report.budget_summary}")
    st.subheader("Campaign recommendations")
    for item in report.campaign_recommendations:
        with st.expander(f"{item.campaign_id} | {_action_label(item.action.value)}"):
            st.markdown(f"**Decision:** {item.decision_explanation}")
            st.markdown(f"**Budget:** {item.budget_explanation}")
            if item.conversation_lessons:
                st.markdown("**Conversation lessons**")
                for lesson in item.conversation_lessons:
                    st.markdown(f"- {lesson}")
    left, right = st.columns(2)
    with left:
        st.subheader("Objective lessons")
        for lesson in report.objective_lessons:
            st.markdown(f"- {lesson}")
        st.subheader("Strategic lessons")
        for lesson in report.strategic_lessons:
            st.markdown(f"- {lesson}")
    with right:
        st.subheader("Test plan")
        for item in report.test_plan_summary:
            st.markdown(f"- {item}")
        st.subheader("Assumptions")
        for assumption in report.assumptions:
            st.markdown(f"- {assumption}")


def _recommendation_view(result: MVPResult, currency: str) -> None:
    st.subheader("Deterministic recommendation")
    _deterministic_recommendation(result, currency)
    st.divider()
    st.subheader("LLM business narration")
    st.caption(
        "The narrator receives validated evidence and can explain it, but cannot change scores, actions, or allocations."
    )
    model = st.text_input("Narration model", value=os.getenv("OPENAI_MODEL", "gpt-5-mini"))
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    if not has_key:
        st.info("Set OPENAI_API_KEY in .env to generate the structured narration.")
    if st.button(
        "Generate business narration", icon=":material/auto_awesome:",
        type="primary", disabled=not has_key,
    ):
        with st.spinner("Generating validated business narration..."):
            try:
                report = run_recommendation(result.recommendation_input, model=model)
                st.session_state["mvp_llm_report"] = report.model_dump(mode="json")
            except Exception as exc:
                st.error(f"The narration could not be generated: {exc}")
    payload = st.session_state.get("mvp_llm_report")
    if payload:
        report = RecommendationReport.model_validate(payload)
        _render_llm_report(report)
        st.download_button(
            "Download narration JSON", data=json.dumps(payload, ensure_ascii=False, indent=2),
            file_name="mvp_recommendation_output.json", mime="application/json",
            icon=":material/download:",
        )


def main() -> None:
    _configure_page()
    input_directory, signals_path, budget, currency = _sidebar()
    try:
        with st.spinner("Building objective scorecards..."):
            result = _load_result(input_directory, signals_path, budget, currency)
    except Exception as exc:
        st.error(f"The MVP report could not be built: {exc}")
        st.stop()
    _header(result)
    tabs = st.tabs(
        [
            "Portfolio", "Objectives", "Campaign", "Entity Scorecards",
            "Customer Insights", "Budget and Tests", "Recommendation",
        ]
    )
    with tabs[0]:
        _portfolio_view(result, currency)
    with tabs[1]:
        _objective_view(result, currency)
    with tabs[2]:
        _campaign_view(result, currency)
    with tabs[3]:
        _entities_view(result)
    with tabs[4]:
        _customer_view(result)
    with tabs[5]:
        _budget_view(result, currency)
    with tabs[6]:
        _recommendation_view(result, currency)


if __name__ == "__main__":
    main()
