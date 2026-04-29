import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_LOG_DIR = "evaluation_logs"
JSON_EXT = ".json"
ANALYSIS_DIR = os.path.join(BASE_LOG_DIR, "analysis")
RECOMMENDATION_DIR = os.path.join(BASE_LOG_DIR, "recommendation")
OVERALL_DIR = os.path.join(BASE_LOG_DIR, "overall")

ANALYSIS_CSV = os.path.join(OVERALL_DIR, "overall_analysis.csv")
RECOMMENDATION_CSV = os.path.join(OVERALL_DIR, "overall_recommendation.csv")


ANALYSIS_COLUMNS = [
    "id",
    "run_id",
    "ts_utc",
    "category",
    "campaign_id",
    "campaign_name",
    "target",
    "judge_model",
    "judge_temp",
    "analysis_generation_model",
    "analysis_generation_temp",
    "recommendation_generation_model",
    "recommendation_generation_temp",
    "overall_score",
    "overall_status",
    "crit_analysis_score",
    "crit_key_signals_score",
    "crit_detected_issues_score",
    "crit_root_cause_hypothesis_score",
    "crit_business_risks_score",
    "crit_confidence_score_score",
    "crit_analysis_rationale",
    "crit_key_signals_rationale",
    "crit_detected_issues_rationale",
    "crit_root_cause_hypothesis_rationale",
    "crit_business_risks_rationale",
    "crit_confidence_score_rationale",
    "summary",
    "improvement_suggestions_count",
    "improvement_suggestions",
    "raw_log_path",
    "pipeline_log_path",
    "ingested_at_utc",
]


RECOMMENDATION_COLUMNS = [
    "id",
    "run_id",
    "ts_utc",
    "category",
    "campaign_id",
    "campaign_name",
    "target",
    "judge_model",
    "judge_temp",
    "analysis_generation_model",
    "analysis_generation_temp",
    "recommendation_generation_model",
    "recommendation_generation_temp",
    "final_score",
    "business_score",
    "business_insight_quality",
    "business_actionability",
    "business_data_grounding",
    "business_kpi_alignment",
    "business_priority_accuracy",
    "business_decision_quality",
    "business_feasibility",
    "business_readability",
    "compliance_score",
    "compliance_count_valid",
    "compliance_required_fields",
    "compliance_priority_order",
    "compliance_no_hallucination",
    "compliance_clarity",
    "compliance_non_repetition",
    "ground_truth_score",
    "gt_avg_similarity",
    "gt_coverage",
    "gt_llm_calls",
    "total_recommendations",
    "total_ground_truth",
    "business_flag_count",
    "compliance_flag_count",
    "gt_flag_count",
    "weak_recommendations_count",
    "has_missing_key_expert_insights",
    "has_low_similarity_to_expert",
    "has_invalid_recommendation_count",
    "has_missing_required_fields",
    "has_priority_not_sorted",
    "has_possible_hallucination",
    "raw_log_path",
    "pipeline_log_path",
    "ingested_at_utc",
]


def _extract_timestamp_from_filename(path: str) -> Optional[datetime]:
    basename = os.path.basename(path)
    if not basename.startswith("eval_") or not basename.endswith(JSON_EXT):
        return None

    raw = basename.replace("eval_", "").replace(JSON_EXT, "")
    parts = raw.split("_")
    if len(parts) >= 3:
        raw = f"{parts[0]}_{parts[1]}"
    try:
        naive = datetime.strptime(raw, "%Y%m%d_%H%M%S")
        return naive.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _to_iso_utc(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _stable_id(path: str) -> str:
    """Deterministic row id derived from the source log file path."""
    return hashlib.md5(path.encode("utf-8")).hexdigest()


def _run_id_from_timestamp(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return dt.strftime("run_%Y%m%d_%H%M%S")


def _timestamp_from_payload(payload: Dict) -> Optional[datetime]:
    raw = payload.get("timestamp_utc", "")
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _safe_read_json(path: str) -> Optional[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _bool_int(condition: bool) -> int:
    return 1 if condition else 0


def _analysis_row(payload: Dict, path: str, ingested_at: str) -> Dict:
    ts = _timestamp_from_payload(payload) or _extract_timestamp_from_filename(path)
    criteria_by_name = {
        criterion.get("name", ""): criterion
        for criterion in payload.get("criteria_scores", [])
    }
    suggestions = payload.get("improvement_suggestions", []) or []

    return {
        "id": _stable_id(path),
        "run_id": payload.get("run_id") or _run_id_from_timestamp(ts),
        "ts_utc": _to_iso_utc(ts),
        "category": payload.get("category", ""),
        "campaign_id": payload.get("campaign_id", ""),
        "campaign_name": payload.get("campaign_name", ""),
        "target": payload.get("target", ""),
        "judge_model": payload.get("judge_model", ""),
        "judge_temp": payload.get("judge_temp", ""),
        "analysis_generation_model": payload.get("analysis_generation_model", ""),
        "analysis_generation_temp": payload.get("analysis_generation_temp", ""),
        "recommendation_generation_model": payload.get(
            "recommendation_generation_model", ""
        ),
        "recommendation_generation_temp": payload.get(
            "recommendation_generation_temp", ""
        ),
        "overall_score": payload.get("overall_score", ""),
        "overall_status": payload.get("overall_status", ""),
        "crit_analysis_score": criteria_by_name.get("analysis", {}).get("score", ""),
        "crit_key_signals_score": criteria_by_name.get("key_signals", {}).get(
            "score", ""
        ),
        "crit_detected_issues_score": criteria_by_name.get("detected_issues", {}).get(
            "score", ""
        ),
        "crit_root_cause_hypothesis_score": criteria_by_name.get(
            "root_cause_hypothesis", {}
        ).get("score", ""),
        "crit_business_risks_score": criteria_by_name.get("business_risks", {}).get(
            "score", ""
        ),
        "crit_confidence_score_score": criteria_by_name.get("confidence_score", {}).get(
            "score", ""
        ),
        "crit_analysis_rationale": criteria_by_name.get("analysis", {}).get(
            "rationale", ""
        ),
        "crit_key_signals_rationale": criteria_by_name.get("key_signals", {}).get(
            "rationale", ""
        ),
        "crit_detected_issues_rationale": criteria_by_name.get(
            "detected_issues", {}
        ).get("rationale", ""),
        "crit_root_cause_hypothesis_rationale": criteria_by_name.get(
            "root_cause_hypothesis", {}
        ).get("rationale", ""),
        "crit_business_risks_rationale": criteria_by_name.get("business_risks", {}).get(
            "rationale", ""
        ),
        "crit_confidence_score_rationale": criteria_by_name.get(
            "confidence_score", {}
        ).get("rationale", ""),
        "summary": payload.get("summary", ""),
        "improvement_suggestions_count": len(suggestions),
        "improvement_suggestions": json.dumps(suggestions, ensure_ascii=False),
        "raw_log_path": path,
        "pipeline_log_path": payload.get("pipeline_log_path", ""),
        "ingested_at_utc": ingested_at,
    }


def _recommendation_row(payload: Dict, path: str, ingested_at: str) -> Dict:
    ts = _timestamp_from_payload(payload) or _extract_timestamp_from_filename(path)
    business = payload.get("business", {}) or {}
    compliance = payload.get("compliance", {}) or {}
    ground_truth = payload.get("ground_truth", {}) or {}
    business_scores = business.get("overall", {}).get("scores", {}) or {}
    compliance_dimensions = compliance.get("dimensions", {}) or {}

    business_flags = business.get("flags", []) or []
    compliance_flags = compliance.get("flags", []) or []
    gt_flags = ground_truth.get("flags", []) or []
    weak = business.get("weak_recommendations", []) or []

    return {
        "id": _stable_id(path),
        "run_id": payload.get("run_id") or _run_id_from_timestamp(ts),
        "ts_utc": _to_iso_utc(ts),
        "category": payload.get("category", ""),
        "campaign_id": payload.get("campaign_id", ""),
        "campaign_name": payload.get("campaign_name", ""),
        "target": payload.get("target", ""),
        "judge_model": payload.get("judge_model", ""),
        "judge_temp": payload.get("judge_temp", ""),
        "analysis_generation_model": payload.get("analysis_generation_model", ""),
        "analysis_generation_temp": payload.get("analysis_generation_temp", ""),
        "recommendation_generation_model": payload.get(
            "recommendation_generation_model", ""
        ),
        "recommendation_generation_temp": payload.get(
            "recommendation_generation_temp", ""
        ),
        "final_score": payload.get("final_score", ""),
        "business_score": business.get("score", ""),
        "business_insight_quality": business_scores.get("insight_quality", ""),
        "business_actionability": business_scores.get("actionability", ""),
        "business_data_grounding": business_scores.get("data_grounding", ""),
        "business_kpi_alignment": business_scores.get("kpi_alignment", ""),
        "business_priority_accuracy": business_scores.get("priority_accuracy", ""),
        "business_decision_quality": business_scores.get("decision_quality", ""),
        "business_feasibility": business_scores.get("feasibility", ""),
        "business_readability": business_scores.get("readability", ""),
        "compliance_score": compliance.get("score", ""),
        "compliance_count_valid": compliance_dimensions.get("count_valid", ""),
        "compliance_required_fields": compliance_dimensions.get("required_fields", ""),
        "compliance_priority_order": compliance_dimensions.get("priority_order", ""),
        "compliance_no_hallucination": compliance_dimensions.get(
            "no_hallucination", ""
        ),
        "compliance_clarity": compliance_dimensions.get("clarity", ""),
        "compliance_non_repetition": compliance_dimensions.get("non_repetition", ""),
        "ground_truth_score": ground_truth.get("score", ""),
        "gt_avg_similarity": ground_truth.get("avg_similarity", ""),
        "gt_coverage": ground_truth.get("coverage", ""),
        "gt_llm_calls": ground_truth.get("llm_calls", ""),
        "total_recommendations": ground_truth.get("total_recommendations", ""),
        "total_ground_truth": ground_truth.get("total_ground_truth", ""),
        "business_flag_count": len(business_flags),
        "compliance_flag_count": len(compliance_flags),
        "gt_flag_count": len(gt_flags),
        "weak_recommendations_count": len(weak),
        "has_missing_key_expert_insights": _bool_int(
            "missing_key_expert_insights" in gt_flags
        ),
        "has_low_similarity_to_expert": _bool_int(
            "low_similarity_to_expert" in gt_flags
        ),
        "has_invalid_recommendation_count": _bool_int(
            "invalid_recommendation_count" in compliance_flags
        ),
        "has_missing_required_fields": _bool_int(
            "missing_required_fields" in compliance_flags
        ),
        "has_priority_not_sorted": _bool_int("priority_not_sorted" in compliance_flags),
        "has_possible_hallucination": _bool_int(
            "possible_hallucination" in compliance_flags
            or "hallucination_detected" in compliance_flags
        ),
        "raw_log_path": path,
        "pipeline_log_path": payload.get("pipeline_log_path", ""),
        "ingested_at_utc": ingested_at,
    }


def _list_json_files(directory: str) -> List[str]:
    if not os.path.exists(directory):
        return []
    files = []
    for name in os.listdir(directory):
        if name.endswith(JSON_EXT):
            files.append(os.path.join(directory, name))
    return sorted(files)


def _write_csv(path: str, columns: List[str], rows: List[Dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def aggregate_logs(ingested_at: Optional[str] = None) -> Dict[str, str]:
    if ingested_at is None:
        ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    analysis_rows = []
    for path in _list_json_files(ANALYSIS_DIR):
        payload = _safe_read_json(path)
        if payload is None:
            continue
        analysis_rows.append(_analysis_row(payload, path, ingested_at))

    recommendation_rows = []
    for path in _list_json_files(RECOMMENDATION_DIR):
        payload = _safe_read_json(path)
        if payload is None:
            continue
        recommendation_rows.append(_recommendation_row(payload, path, ingested_at))

    _write_csv(ANALYSIS_CSV, ANALYSIS_COLUMNS, analysis_rows)
    _write_csv(
        RECOMMENDATION_CSV,
        RECOMMENDATION_COLUMNS,
        recommendation_rows,
    )

    return {
        "overall_analysis_csv": ANALYSIS_CSV,
        "overall_recommendation_csv": RECOMMENDATION_CSV,
        "analysis_rows": str(len(analysis_rows)),
        "recommendation_rows": str(len(recommendation_rows)),
    }


def main() -> None:
    result = aggregate_logs()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
