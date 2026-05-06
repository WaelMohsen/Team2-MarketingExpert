from src.evaluation.dashboard_data import (
    filter_dashboard_frame,
    load_dashboard_frame,
    metric_bounds,
    resolve_metric_rationale,
    summarize_all_metrics_by_run,
    summarize_by_run,
    summarize_selected_metric_by_dimension,
    summarize_selected_metric_by_run,
)


def test_load_dashboard_frame_analysis_has_expected_columns():
    frame = load_dashboard_frame("Analysis")

    assert not frame.empty
    assert "record_label" in frame.columns
    assert str(frame["ts_utc"].dtype).startswith("datetime64")


def test_summarize_by_run_keeps_model_metadata_for_hover():
    frame = load_dashboard_frame("Recommendation")

    summary = summarize_by_run(frame, "Recommendation")

    assert not summary.empty
    assert "analysis_generation_model" in summary.columns
    assert "analysis_generation_temp" in summary.columns
    assert "recommendation_generation_model" in summary.columns
    assert "judge_model" in summary.columns
    assert "judge_temp" in summary.columns


def test_resolve_analysis_metric_rationale_from_aggregate_csv():
    frame = load_dashboard_frame("Analysis")

    rationale = resolve_metric_rationale(
        "Analysis", frame.iloc[0], "crit_analysis_score"
    )

    assert rationale["source"] == "aggregate_csv"
    assert rationale["text"]


def test_resolve_recommendation_business_metric_rationale_from_raw_json():
    frame = load_dashboard_frame("Recommendation")
    row = frame.loc[
        frame["raw_log_path"].str.contains("eval_20260501_204227_revenue_growth.json")
    ].iloc[0]

    rationale = resolve_metric_rationale(
        "Recommendation", row, "business_actionability"
    )

    assert rationale["source"] == "raw_json"
    assert "Steps are generally clear" in rationale["text"]


def test_filter_dashboard_frame_applies_selected_metric_range():
    frame = load_dashboard_frame("Recommendation")
    target_value = float(frame.iloc[0]["business_actionability"])

    filtered = filter_dashboard_frame(
        frame,
        filters={},
        metric_column="business_actionability",
        metric_range=(target_value, target_value),
    )

    assert not filtered.empty
    assert set(filtered["business_actionability"].astype(float)) == {target_value}


def test_metric_bounds_returns_numeric_range_for_selected_metric():
    frame = load_dashboard_frame("Analysis")

    bounds = metric_bounds(frame, "crit_analysis_score")

    assert bounds is not None
    assert bounds[0] <= bounds[1]


def test_summarize_all_metrics_by_run_returns_metric_labels():
    frame = load_dashboard_frame("Analysis")

    summary = summarize_all_metrics_by_run(frame, "Analysis")

    assert not summary.empty
    assert "metric_label" in summary.columns
    assert "avg_metric" in summary.columns


def test_summarize_selected_metric_by_run_uses_metric_column():
    frame = load_dashboard_frame("Recommendation")

    summary = summarize_selected_metric_by_run(frame, "business_actionability")

    assert not summary.empty
    assert "avg_metric" in summary.columns
    actual = summary.set_index("run_id").iloc[0]["avg_metric"]
    assert actual in frame.groupby("run_id")["business_actionability"].mean().values


def test_summarize_selected_metric_by_dimension_uses_metric_column():
    frame = load_dashboard_frame("Analysis")

    summary = summarize_selected_metric_by_dimension(
        frame, "crit_analysis_score", "target"
    )

    assert not summary.empty
    assert "avg_metric" in summary.columns
