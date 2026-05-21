from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src.evaluation.dashboard_data import (
    MODE_CONFIG,
    available_metrics,
    filter_dashboard_frame,
    load_dashboard_frame,
    metric_bounds,
    resolve_metric_rationale,
    summarize_all_metrics_by_run,
    summarize_metric,
    summarize_selected_metric_by_dimension,
    summarize_selected_metric_by_run,
)

ANALYSIS_MODEL_LABEL = "Analysis model"
RECOMMENDATION_MODEL_LABEL = "Recommendation model"
JUDGE_MODEL_LABEL = "Judge model"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M UTC"
LATEST_ROW_LABEL = "Latest row"
AVG_SCORE_ENCODING = "avg_score:Q"
AVG_METRIC_ENCODING = "avg_metric:Q"
RUN_ID_ENCODING = "run_id:N"
METRIC_LABEL_ENCODING = "metric_label:N"
TIMESTAMP_ENCODING = "ts_utc:T"
AVERAGE_SCORE_LABEL = "Average score"
AVERAGE_METRIC_LABEL = "Average metric"


st.set_page_config(
    page_title="Evaluation Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_mode_frame(mode: str) -> pd.DataFrame:
    return load_dashboard_frame(mode)


def main() -> None:
    st.title("Evaluation Dashboard")
    st.caption(
        "Track evaluation quality by run, campaign, and target. Hover a run to see the exact models and temperatures used."
    )

    with st.sidebar:
        st.header("Controls")
        mode = st.radio("Evaluation mode", ["Analysis", "Recommendation"])
        frame = load_mode_frame(mode)

        if frame.empty:
            st.warning(
                f"No aggregated rows were found for {mode.lower()} evaluation. Run the aggregator first."
            )
            st.stop()

        metric_options = available_metrics(mode)
        selected_metric_label = st.selectbox("Metric", list(metric_options.keys()))
        selected_metric = metric_options[selected_metric_label]
        selected_metric_range = build_metric_range_slider(
            frame, selected_metric, selected_metric_label
        )

        date_range = build_date_range(frame)
        filters = {
            "run_id": st.multiselect(
                "Run", sorted(frame["run_id"].dropna().astype(str).unique())
            ),
            "campaign_name": st.multiselect(
                "Campaign", sorted(frame["campaign_name"].dropna().astype(str).unique())
            ),
            "target": st.multiselect(
                "Target", sorted(frame["target"].dropna().astype(str).unique())
            ),
            "category": st.multiselect(
                "Category", sorted(frame["category"].dropna().astype(str).unique())
            ),
            "analysis_generation_model": st.multiselect(
                ANALYSIS_MODEL_LABEL,
                sorted(
                    frame["analysis_generation_model"].dropna().astype(str).unique()
                ),
            ),
            "recommendation_generation_model": st.multiselect(
                RECOMMENDATION_MODEL_LABEL,
                sorted(
                    frame["recommendation_generation_model"]
                    .dropna()
                    .astype(str)
                    .unique()
                ),
            ),
            "judge_model": st.multiselect(
                JUDGE_MODEL_LABEL,
                sorted(frame["judge_model"].dropna().astype(str).unique()),
            ),
        }

    filtered = filter_dashboard_frame(
        frame,
        filters,
        date_range,
        metric_column=selected_metric,
        metric_range=selected_metric_range,
    )
    if filtered.empty:
        st.info("No rows match the selected filters.")
        return

    render_summary_cards(filtered, mode, selected_metric_label, selected_metric)
    st.divider()

    selected_metric_run_summary = summarize_selected_metric_by_run(
        filtered, selected_metric
    )
    all_metrics_by_run = summarize_all_metrics_by_run(filtered, mode)
    campaign_summary = summarize_selected_metric_by_dimension(
        filtered,
        selected_metric,
        "campaign_name",
    )
    target_summary = summarize_selected_metric_by_dimension(
        filtered,
        selected_metric,
        "target",
    )
    metric_breakdown = summarize_metric(filtered, selected_metric, "target")

    st.subheader(f"Run Overview: {selected_metric_label}")
    st.altair_chart(
        build_run_chart(selected_metric_run_summary, selected_metric_label),
        use_container_width=True,
    )
    st.dataframe(
        format_run_summary(selected_metric_run_summary, selected_metric_label),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("All Metric Scores per Run")
    st.altair_chart(
        build_all_metrics_run_chart(all_metrics_by_run), use_container_width=True
    )
    st.dataframe(
        format_all_metrics_run_summary(all_metrics_by_run),
        use_container_width=True,
        hide_index=True,
    )

    left, right = st.columns(2)
    with left:
        st.subheader(f"Campaign Summary: {selected_metric_label}")
        st.altair_chart(
            build_dimension_chart(
                campaign_summary, "campaign_name", selected_metric_label
            ),
            use_container_width=True,
        )
        st.dataframe(
            format_dimension_summary(
                campaign_summary, "campaign_name", selected_metric_label
            ),
            use_container_width=True,
            hide_index=True,
        )
    with right:
        st.subheader(f"Target Summary: {selected_metric_label}")
        st.altair_chart(
            build_dimension_chart(target_summary, "target", selected_metric_label),
            use_container_width=True,
        )
        st.dataframe(
            format_dimension_summary(target_summary, "target", selected_metric_label),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader(f"Metric Breakdown: {selected_metric_label}")
    st.altair_chart(
        build_metric_chart(metric_breakdown, "target"), use_container_width=True
    )
    st.dataframe(
        format_metric_breakdown(metric_breakdown, "target"),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Rationale Drill-down")
    selected_record_label = st.selectbox(
        "Inspect a specific evaluation row",
        filtered["record_label"].tolist(),
    )
    selected_row = filtered.loc[filtered["record_label"] == selected_record_label].iloc[
        0
    ]
    render_record_details(selected_row, mode, selected_metric_label, selected_metric)


def build_date_range(frame: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    valid_dates = frame["ts_utc"].dropna()
    if valid_dates.empty:
        return None

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()
    selected_start, selected_end = st.slider(
        "Date range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD",
    )

    return (
        pd.Timestamp(selected_start, tz="UTC"),
        pd.Timestamp(selected_end, tz="UTC"),
    )


def build_metric_range_slider(
    frame: pd.DataFrame,
    metric_column: str,
    metric_label: str,
) -> tuple[float, float] | None:
    bounds = metric_bounds(frame, metric_column)
    if bounds is None:
        return None

    min_value, max_value = bounds
    if min_value == max_value:
        st.caption(
            f"{metric_label} is fixed at {format_score(min_value)} for the current dataset."
        )
        return (min_value, max_value)

    return st.slider(
        f"{metric_label} score range",
        min_value=min_value,
        max_value=max_value,
        value=(min_value, max_value),
        step=0.01,
    )


def render_summary_cards(
    frame: pd.DataFrame,
    mode: str,
    metric_label: str,
    metric_column: str,
) -> None:
    score_column = MODE_CONFIG[mode]["score_column"]
    columns = st.columns(5)
    latest_ts = frame["ts_utc"].max()
    status_value, status_label = status_metric(frame, mode)
    metric_average = (
        frame[metric_column].mean() if metric_column in frame.columns else None
    )

    metrics = [
        ("Rows", f"{len(frame):,}"),
        ("Runs", f"{frame['run_id'].nunique():,}"),
        (MODE_CONFIG[mode]["score_label"], format_score(frame[score_column].mean())),
        (metric_label, format_score(metric_average)),
        (
            LATEST_ROW_LABEL,
            latest_ts.strftime(TIMESTAMP_FORMAT) if pd.notna(latest_ts) else "n/a",
        ),
        (status_label, status_value),
    ]

    for column, (label, value) in zip(columns, metrics):
        column.metric(label, value)


def status_metric(frame: pd.DataFrame, mode: str) -> tuple[str, str]:
    if mode == "Analysis":
        pass_count = int((frame["overall_status"] == "pass").sum())
        return str(pass_count), "Pass rows"

    flag_count = int(frame["gt_flag_count"].fillna(0).sum())
    return str(flag_count), "GT flag count"


def build_run_chart(run_summary: pd.DataFrame, metric_label: str) -> alt.Chart:
    return (
        alt.Chart(run_summary)
        .mark_line(point=alt.OverlayMarkDef(size=110, filled=True), strokeWidth=2)
        .encode(
            x=alt.X(TIMESTAMP_ENCODING, title="Run timestamp"),
            y=alt.Y(AVG_METRIC_ENCODING, title=metric_label),
            color=alt.Color("campaign_name:N", title="Campaign"),
            tooltip=[
                alt.Tooltip(RUN_ID_ENCODING, title="Run"),
                alt.Tooltip(TIMESTAMP_ENCODING, title="Timestamp"),
                alt.Tooltip(AVG_METRIC_ENCODING, title=metric_label, format=".3f"),
                alt.Tooltip("record_count:Q", title="Rows"),
                alt.Tooltip("analysis_generation_model:N", title=ANALYSIS_MODEL_LABEL),
                alt.Tooltip("analysis_generation_temp:N", title="Analysis temp"),
                alt.Tooltip(
                    "recommendation_generation_model:N",
                    title=RECOMMENDATION_MODEL_LABEL,
                ),
                alt.Tooltip(
                    "recommendation_generation_temp:N", title="Recommendation temp"
                ),
                alt.Tooltip("judge_model:N", title=JUDGE_MODEL_LABEL),
                alt.Tooltip("judge_temp:N", title="Judge temp"),
            ],
        )
        .properties(height=320)
    )


def build_dimension_chart(
    summary: pd.DataFrame, dimension: str, metric_label: str
) -> alt.Chart:
    return (
        alt.Chart(summary)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{dimension}:N", sort="-y", title=dimension.replace("_", " ").title()
            ),
            y=alt.Y(AVG_METRIC_ENCODING, title=metric_label),
            tooltip=[
                alt.Tooltip(
                    f"{dimension}:N", title=dimension.replace("_", " ").title()
                ),
                alt.Tooltip(AVG_METRIC_ENCODING, title=metric_label, format=".3f"),
                alt.Tooltip("row_count:Q", title="Rows"),
                alt.Tooltip("latest_ts:T", title=LATEST_ROW_LABEL),
            ],
        )
        .properties(height=280)
    )


def build_metric_chart(summary: pd.DataFrame, dimension: str) -> alt.Chart:
    return (
        alt.Chart(summary)
        .mark_bar(color="#5b8ff9")
        .encode(
            x=alt.X(
                f"{dimension}:N", sort="-y", title=dimension.replace("_", " ").title()
            ),
            y=alt.Y(AVG_METRIC_ENCODING, title=AVERAGE_METRIC_LABEL),
            tooltip=[
                alt.Tooltip(
                    f"{dimension}:N", title=dimension.replace("_", " ").title()
                ),
                alt.Tooltip(
                    AVG_METRIC_ENCODING, title=AVERAGE_METRIC_LABEL, format=".3f"
                ),
                alt.Tooltip("row_count:Q", title="Rows"),
            ],
        )
        .properties(height=280)
    )


def build_all_metrics_run_chart(summary: pd.DataFrame) -> alt.Chart:
    if summary.empty:
        return alt.Chart(pd.DataFrame({"message": []})).mark_bar()

    return (
        alt.Chart(summary)
        .mark_bar()
        .encode(
            x=alt.X(RUN_ID_ENCODING, title="Run", sort="-y"),
            y=alt.Y(AVG_METRIC_ENCODING, title=AVERAGE_METRIC_LABEL),
            color=alt.Color(METRIC_LABEL_ENCODING, title="Metric"),
            xOffset=alt.XOffset(METRIC_LABEL_ENCODING),
            tooltip=[
                alt.Tooltip(RUN_ID_ENCODING, title="Run"),
                alt.Tooltip(METRIC_LABEL_ENCODING, title="Metric"),
                alt.Tooltip(
                    AVG_METRIC_ENCODING, title=AVERAGE_METRIC_LABEL, format=".3f"
                ),
                alt.Tooltip("campaign_name:N", title="Campaign"),
                alt.Tooltip(TIMESTAMP_ENCODING, title="Timestamp"),
            ],
        )
        .properties(height=340)
    )


def format_run_summary(run_summary: pd.DataFrame, metric_label: str) -> pd.DataFrame:
    display = run_summary.copy()
    display["ts_utc"] = display["ts_utc"].dt.strftime(TIMESTAMP_FORMAT)
    display["avg_metric"] = display["avg_metric"].map(format_score)
    display = display.rename(
        columns={
            "run_id": "Run",
            "ts_utc": "Timestamp",
            "record_count": "Rows",
            "campaign_name": "Campaign",
            "target": "Targets",
            "category": "Categories",
            "avg_metric": metric_label,
            "analysis_generation_model": ANALYSIS_MODEL_LABEL,
            "analysis_generation_temp": "Analysis temp",
            "recommendation_generation_model": RECOMMENDATION_MODEL_LABEL,
            "recommendation_generation_temp": "Recommendation temp",
            "judge_model": JUDGE_MODEL_LABEL,
            "judge_temp": "Judge temp",
        }
    )
    return display


def format_dimension_summary(
    summary: pd.DataFrame, dimension: str, metric_label: str
) -> pd.DataFrame:
    display = summary.copy()
    display["avg_metric"] = display["avg_metric"].map(format_score)
    display["latest_ts"] = display["latest_ts"].dt.strftime(TIMESTAMP_FORMAT)
    display = display.rename(
        columns={
            dimension: dimension.replace("_", " ").title(),
            "row_count": "Rows",
            "avg_metric": metric_label,
            "latest_ts": LATEST_ROW_LABEL,
        }
    )
    return display


def format_metric_breakdown(summary: pd.DataFrame, dimension: str) -> pd.DataFrame:
    display = summary.copy()
    display["avg_metric"] = display["avg_metric"].map(format_score)
    return display.rename(
        columns={
            dimension: dimension.replace("_", " ").title(),
            "row_count": "Rows",
            "avg_metric": AVERAGE_METRIC_LABEL,
        }
    )


def format_all_metrics_run_summary(summary: pd.DataFrame) -> pd.DataFrame:
    display = summary.copy()
    if display.empty:
        return display

    display["ts_utc"] = display["ts_utc"].dt.strftime(TIMESTAMP_FORMAT)
    display["avg_metric"] = display["avg_metric"].map(format_score)
    return display.rename(
        columns={
            "run_id": "Run",
            "metric_label": "Metric",
            "avg_metric": AVERAGE_METRIC_LABEL,
            "campaign_name": "Campaign",
            "ts_utc": "Timestamp",
        }
    )


def render_record_details(
    row: pd.Series,
    mode: str,
    metric_label: str,
    metric_column: str,
) -> None:
    rationale = resolve_metric_rationale(mode, row, metric_column)

    metadata_columns = st.columns(3)
    metadata_columns[0].markdown(
        f"**Run**: {row['run_id']}  \n**Campaign**: {row['campaign_name']}  \n**Target**: {row['target']}"
    )
    metadata_columns[1].markdown(
        f"**Analysis model**: {row['analysis_generation_model']} ({row['analysis_generation_temp']})  \n**Recommendation model**: {row['recommendation_generation_model']} ({row['recommendation_generation_temp']})"
    )
    metadata_columns[2].markdown(
        f"**Judge model**: {row['judge_model']} ({row['judge_temp']})  \n**Metric**: {metric_label}"
    )

    st.markdown(f"### {metric_label}")
    st.write(rationale["text"])
    if rationale["details"]:
        with st.expander("Supporting evidence", expanded=True):
            for detail in rationale["details"]:
                st.write(f"- {detail}")

    st.caption(
        f"Source: {rationale['source']} | Raw log: {row.get('raw_log_path', 'n/a')} | Pipeline log: {row.get('pipeline_log_path', 'n/a')}"
    )


def format_score(value: float | int | str) -> str:
    if pd.isna(value):
        return "n/a"
    if isinstance(value, str):
        return value
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    main()
