from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
OVERALL_DIR = ROOT_DIR / "evaluation_logs" / "overall"

MODE_CONFIG = {
    "Analysis": {
        "csv_path": OVERALL_DIR / "overall_analysis.csv",
        "score_column": "overall_score",
        "score_label": "Overall score",
    },
    "Recommendation": {
        "csv_path": OVERALL_DIR / "overall_recommendation.csv",
        "score_column": "final_score",
        "score_label": "Final score",
    },
}

ANALYSIS_METRICS = {
    "Overall score": "overall_score",
    "Analysis quality": "crit_analysis_score",
    "Key signals": "crit_key_signals_score",
    "Detected issues": "crit_detected_issues_score",
    "Root cause hypothesis": "crit_root_cause_hypothesis_score",
    "Business risks": "crit_business_risks_score",
    "Confidence score": "crit_confidence_score_score",
}

ANALYSIS_RATIONALES = {
    "crit_analysis_score": "crit_analysis_rationale",
    "crit_key_signals_score": "crit_key_signals_rationale",
    "crit_detected_issues_score": "crit_detected_issues_rationale",
    "crit_root_cause_hypothesis_score": "crit_root_cause_hypothesis_rationale",
    "crit_business_risks_score": "crit_business_risks_rationale",
    "crit_confidence_score_score": "crit_confidence_score_rationale",
}

RECOMMENDATION_METRICS = {
    "Final score": "final_score",
    "Business score": "business_score",
    "Insight quality": "business_insight_quality",
    "Actionability": "business_actionability",
    "Data grounding": "business_data_grounding",
    "KPI alignment": "business_kpi_alignment",
    "Priority accuracy": "business_priority_accuracy",
    "Decision quality": "business_decision_quality",
    "Feasibility": "business_feasibility",
    "Readability": "business_readability",
    "Compliance score": "compliance_score",
    "Valid count": "compliance_count_valid",
    "Required fields": "compliance_required_fields",
    "Priority order": "compliance_priority_order",
    "No hallucination": "compliance_no_hallucination",
    "Clarity": "compliance_clarity",
    "Non repetition": "compliance_non_repetition",
    "Ground truth score": "ground_truth_score",
    "Average similarity": "gt_avg_similarity",
    "Coverage": "gt_coverage",
}

BUSINESS_EXPLANATION_KEYS = {
    "business_insight_quality": "insight_quality",
    "business_actionability": "actionability",
    "business_data_grounding": "data_grounding",
    "business_kpi_alignment": "kpi_alignment",
    "business_priority_accuracy": "priority_accuracy",
    "business_decision_quality": "decision_quality",
    "business_feasibility": "feasibility",
    "business_readability": "readability",
}

TEXT_COLUMNS = {
    "id",
    "run_id",
    "category",
    "campaign_id",
    "campaign_name",
    "target",
    "judge_model",
    "analysis_generation_model",
    "recommendation_generation_model",
    "overall_status",
    "summary",
    "improvement_suggestions",
    "raw_log_path",
    "pipeline_log_path",
    "ingested_at_utc",
    "record_label",
}

RAW_JSON_SOURCE = "raw_json"


def available_metrics(mode: str) -> Dict[str, str]:
    if mode == "Analysis":
        return ANALYSIS_METRICS
    if mode == "Recommendation":
        return RECOMMENDATION_METRICS
    raise ValueError(f"Unsupported mode: {mode}")


def load_dashboard_frame(mode: str) -> pd.DataFrame:
    config = MODE_CONFIG.get(mode)
    if config is None:
        raise ValueError(f"Unsupported mode: {mode}")

    csv_path = Path(config["csv_path"])
    if not csv_path.exists():
        return pd.DataFrame()

    frame = pd.read_csv(csv_path)
    if frame.empty:
        return frame

    frame["ts_utc"] = pd.to_datetime(frame["ts_utc"], utc=True, errors="coerce")
    frame["ingested_at_utc"] = pd.to_datetime(
        frame["ingested_at_utc"], utc=True, errors="coerce"
    )

    numeric_columns = [column for column in frame.columns if column not in TEXT_COLUMNS]
    for column in numeric_columns:
        if column in {"ts_utc", "ingested_at_utc"}:
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        if not converted.isna().all():
            frame[column] = converted

    frame["record_label"] = frame.apply(_record_label, axis=1)
    return frame.sort_values("ts_utc", ascending=False).reset_index(drop=True)


def filter_dashboard_frame(
    frame: pd.DataFrame,
    filters: Dict[str, list[str]],
    date_range: tuple[pd.Timestamp, pd.Timestamp] | None = None,
    metric_column: str | None = None,
    metric_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    if frame.empty:
        return frame

    filtered = frame.copy()
    for column, selected_values in filters.items():
        if selected_values:
            filtered = filtered[filtered[column].isin(selected_values)]

    if date_range is not None:
        start, end = date_range
        filtered = filtered[
            filtered["ts_utc"].between(
                start, end + pd.Timedelta(days=1), inclusive="left"
            )
        ]

    if metric_column and metric_range is not None and metric_column in filtered.columns:
        min_value, max_value = metric_range
        filtered = filtered[
            filtered[metric_column].between(min_value, max_value, inclusive="both")
        ]

    return filtered.reset_index(drop=True)


def metric_bounds(
    frame: pd.DataFrame, metric_column: str
) -> tuple[float, float] | None:
    if frame.empty or metric_column not in frame.columns:
        return None

    metric_values = pd.to_numeric(frame[metric_column], errors="coerce").dropna()
    if metric_values.empty:
        return None

    return float(metric_values.min()), float(metric_values.max())


def summarize_by_run(frame: pd.DataFrame, mode: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    score_column = MODE_CONFIG[mode]["score_column"]
    grouped = frame.groupby("run_id", dropna=False)
    summary = grouped.agg(
        ts_utc=("ts_utc", "max"),
        record_count=("id", "count"),
        campaign_name=("campaign_name", _unique_values),
        target=("target", _unique_values),
        category=("category", _unique_values),
        avg_score=(score_column, "mean"),
        analysis_generation_model=("analysis_generation_model", _unique_values),
        analysis_generation_temp=("analysis_generation_temp", _unique_values),
        recommendation_generation_model=(
            "recommendation_generation_model",
            _unique_values,
        ),
        recommendation_generation_temp=(
            "recommendation_generation_temp",
            _unique_values,
        ),
        judge_model=("judge_model", _unique_values),
        judge_temp=("judge_temp", _unique_values),
    ).reset_index()

    if mode == "Analysis":
        status_counts = grouped["overall_status"].apply(
            lambda values: int((values == "pass").sum())
        )
        summary["status_count"] = (
            summary["run_id"].map(status_counts).fillna(0).astype(int)
        )
        summary["status_label"] = "Pass rows"
    else:
        flag_counts = grouped["gt_flag_count"].sum().fillna(0).astype(int)
        summary["status_count"] = (
            summary["run_id"].map(flag_counts).fillna(0).astype(int)
        )
        summary["status_label"] = "GT flag count"

    return summary.sort_values("ts_utc", ascending=False).reset_index(drop=True)


def summarize_by_dimension(
    frame: pd.DataFrame, mode: str, dimension: str
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    score_column = MODE_CONFIG[mode]["score_column"]
    summary = (
        frame.groupby(dimension, dropna=False)
        .agg(
            row_count=("id", "count"),
            avg_score=(score_column, "mean"),
            latest_ts=("ts_utc", "max"),
        )
        .reset_index()
        .sort_values(["avg_score", "row_count"], ascending=[False, False])
    )
    return summary


def summarize_selected_metric_by_run(
    frame: pd.DataFrame, metric_column: str
) -> pd.DataFrame:
    if frame.empty or metric_column not in frame.columns:
        return pd.DataFrame()

    grouped = frame.groupby("run_id", dropna=False)
    summary = grouped.agg(
        ts_utc=("ts_utc", "max"),
        record_count=("id", "count"),
        campaign_name=("campaign_name", _unique_values),
        target=("target", _unique_values),
        category=("category", _unique_values),
        avg_metric=(metric_column, "mean"),
        analysis_generation_model=("analysis_generation_model", _unique_values),
        analysis_generation_temp=("analysis_generation_temp", _unique_values),
        recommendation_generation_model=(
            "recommendation_generation_model",
            _unique_values,
        ),
        recommendation_generation_temp=(
            "recommendation_generation_temp",
            _unique_values,
        ),
        judge_model=("judge_model", _unique_values),
        judge_temp=("judge_temp", _unique_values),
    ).reset_index()

    return summary.sort_values("ts_utc", ascending=False).reset_index(drop=True)


def summarize_selected_metric_by_dimension(
    frame: pd.DataFrame,
    metric_column: str,
    dimension: str,
) -> pd.DataFrame:
    if frame.empty or metric_column not in frame.columns:
        return pd.DataFrame()

    summary = (
        frame.groupby(dimension, dropna=False)
        .agg(
            row_count=("id", "count"),
            avg_metric=(metric_column, "mean"),
            latest_ts=("ts_utc", "max"),
        )
        .reset_index()
        .sort_values(["avg_metric", "row_count"], ascending=[False, False])
    )
    return summary


def summarize_metric(
    frame: pd.DataFrame, metric_column: str, dimension: str
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    summary = (
        frame.groupby(dimension, dropna=False)
        .agg(row_count=("id", "count"), avg_metric=(metric_column, "mean"))
        .reset_index()
        .sort_values(["avg_metric", "row_count"], ascending=[False, False])
    )
    return summary


def summarize_all_metrics_by_run(frame: pd.DataFrame, mode: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    metric_map = available_metrics(mode)
    metric_columns = [
        column for column in metric_map.values() if column in frame.columns
    ]
    if not metric_columns:
        return pd.DataFrame()

    grouped = frame.groupby("run_id", dropna=False)
    run_metadata = grouped.agg(
        ts_utc=("ts_utc", "max"),
        campaign_name=("campaign_name", _unique_values),
    )
    metric_summary = grouped[metric_columns].mean(numeric_only=True)
    summary = metric_summary.join(run_metadata).reset_index()

    long_frame = summary.melt(
        id_vars=["run_id", "ts_utc", "campaign_name"],
        value_vars=metric_columns,
        var_name="metric_column",
        value_name="avg_metric",
    )
    label_lookup = {column: label for label, column in metric_map.items()}
    long_frame["metric_label"] = long_frame["metric_column"].map(label_lookup)

    return (
        long_frame.dropna(subset=["avg_metric"])
        .sort_values(["ts_utc", "metric_label"], ascending=[False, True])
        .reset_index(drop=True)
    )


def resolve_metric_rationale(
    mode: str, row: pd.Series, metric_column: str
) -> Dict[str, Any]:
    if mode == "Analysis":
        return _resolve_analysis_rationale(row, metric_column)
    if mode == "Recommendation":
        return _resolve_recommendation_rationale(row, metric_column)
    raise ValueError(f"Unsupported mode: {mode}")


def _record_label(row: pd.Series) -> str:
    timestamp = row.get("ts_utc")
    if isinstance(timestamp, pd.Timestamp) and not pd.isna(timestamp):
        ts_text = timestamp.strftime("%Y-%m-%d %H:%M UTC")
    else:
        ts_text = "Unknown time"

    campaign = row.get("campaign_name") or row.get("campaign_id") or "Unknown campaign"
    target = row.get("target") or row.get("category") or "Unknown target"
    run_id = row.get("run_id") or "No run"
    return f"{ts_text} | {campaign} | {target} | {run_id}"


def _unique_values(values: pd.Series) -> str:
    unique = [
        str(value)
        for value in values.dropna().astype(str).unique()
        if str(value).strip()
    ]
    return ", ".join(unique)


def _resolve_analysis_rationale(row: pd.Series, metric_column: str) -> Dict[str, Any]:
    if metric_column == "overall_score":
        return {
            "text": row.get("summary")
            or "No overall summary is available for this analysis row.",
            "details": _analysis_supporting_details(row),
            "source": "aggregate_csv",
        }

    rationale_column = ANALYSIS_RATIONALES.get(metric_column)
    rationale = row.get(rationale_column, "") if rationale_column else ""
    return {
        "text": rationale
        or "No rationale is available for the selected analysis metric.",
        "details": _analysis_supporting_details(row),
        "source": "aggregate_csv",
    }


def _analysis_supporting_details(row: pd.Series) -> list[str]:
    details = []
    summary = row.get("summary")
    if isinstance(summary, str) and summary.strip():
        details.append(f"Summary: {summary}")

    raw_suggestions = row.get("improvement_suggestions")
    if isinstance(raw_suggestions, str) and raw_suggestions.strip():
        try:
            suggestions = json.loads(raw_suggestions)
        except json.JSONDecodeError:
            suggestions = []
        if suggestions:
            details.extend(
                [f"Improvement suggestion: {suggestion}" for suggestion in suggestions]
            )
    return details


def _resolve_recommendation_rationale(
    row: pd.Series, metric_column: str
) -> Dict[str, Any]:
    payload = _load_raw_payload(row.get("raw_log_path", ""))
    if not payload:
        return {
            "text": "The raw recommendation log could not be loaded for this row.",
            "details": [],
            "source": "missing_raw_log",
        }

    if metric_column == "final_score":
        return _final_score_rationale(payload)

    explanation_key = BUSINESS_EXPLANATION_KEYS.get(metric_column)
    if explanation_key:
        return _business_metric_rationale(payload, explanation_key)

    if metric_column.startswith("compliance_") or metric_column == "compliance_score":
        return _compliance_metric_rationale(payload)

    if metric_column.startswith("gt_") or metric_column == "ground_truth_score":
        return _ground_truth_metric_rationale(payload)

    return {
        "text": "No rationale mapping is defined for the selected recommendation metric.",
        "details": _recommendation_supporting_details(payload),
        "source": RAW_JSON_SOURCE,
    }


def _final_score_rationale(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": (
            f"Final score combines business {payload.get('business', {}).get('score', 'n/a')}, "
            f"compliance {payload.get('compliance', {}).get('score', 'n/a')}, and ground truth "
            f"{payload.get('ground_truth', {}).get('score', 'n/a')}."
        ),
        "details": _recommendation_supporting_details(payload),
        "source": RAW_JSON_SOURCE,
    }


def _business_metric_rationale(
    payload: Dict[str, Any], explanation_key: str
) -> Dict[str, Any]:
    explanation = (
        payload.get("business", {})
        .get("overall", {})
        .get("explanations", {})
        .get(explanation_key, "")
    )
    return {
        "text": explanation or "No business explanation is available for this metric.",
        "details": _business_metric_details(payload, explanation_key),
        "source": RAW_JSON_SOURCE,
    }


def _compliance_metric_rationale(payload: Dict[str, Any]) -> Dict[str, Any]:
    compliance = payload.get("compliance", {}) or {}
    flags = compliance.get("flags", []) or []
    dimensions = compliance.get("dimensions", {}) or {}
    detail_lines = [f"Compliance flag: {flag}" for flag in flags]
    detail_lines.extend(
        [
            f"{name.replace('_', ' ').title()}: {value}"
            for name, value in dimensions.items()
        ]
    )
    text = "Compliance metrics are derived from structural validation and rule checks."
    if flags:
        text += f" Active flags: {', '.join(flags)}."
    return {"text": text, "details": detail_lines, "source": RAW_JSON_SOURCE}


def _ground_truth_metric_rationale(payload: Dict[str, Any]) -> Dict[str, Any]:
    ground_truth = payload.get("ground_truth", {}) or {}
    flags = ground_truth.get("flags", []) or []
    matches = ground_truth.get("matches", []) or []
    match_lines = [
        f"{match.get('rec_id', 'Unknown rec')} matched {match.get('matched_gt_id', 'Unknown GT')} with similarity {match.get('similarity', 'n/a')}"
        for match in matches[:5]
    ]
    text = "Ground truth metrics compare generated recommendations against expert references."
    if flags:
        text += f" Active flags: {', '.join(flags)}."
    return {
        "text": text,
        "details": match_lines,
        "source": RAW_JSON_SOURCE,
    }


def _business_metric_details(payload: Dict[str, Any], metric_key: str) -> list[str]:
    recommendations = payload.get("business", {}).get("per_recommendation", []) or []
    details = []
    for recommendation in recommendations:
        metric_value = recommendation.get("scores", {}).get(metric_key)
        issues = recommendation.get("issues", []) or []
        summary = f"{recommendation.get('id', 'Unknown rec')}: score={metric_value}"
        if issues:
            summary += f" | issues={'; '.join(issues)}"
        details.append(summary)
    return details


def _recommendation_supporting_details(payload: Dict[str, Any]) -> list[str]:
    business = payload.get("business", {}) or {}
    compliance = payload.get("compliance", {}) or {}
    ground_truth = payload.get("ground_truth", {}) or {}
    return [
        f"Business score: {business.get('score', 'n/a')}",
        f"Compliance score: {compliance.get('score', 'n/a')}",
        f"Ground truth score: {ground_truth.get('score', 'n/a')}",
    ]


def _load_raw_payload(raw_path: str) -> Dict[str, Any] | None:
    if not raw_path:
        return None

    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT_DIR / path

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
