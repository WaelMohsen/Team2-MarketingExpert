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
    "target",
    "analysis_score",
    "dim_clarity",
    "dim_data_grounding",
    "dim_logic_coherence",
    "dim_business_focus",
    "dim_confidence_calibration",
    "dim_no_recommendation",
    "flag_count",
    "has_low_clarity",
    "has_low_data_grounding",
    "has_low_logic_coherence",
    "has_low_business_focus",
    "has_low_confidence_calibration",
    "has_low_no_recommendation",
    "has_analysis_contains_recommendations",
    "has_llm_failed",
    "raw_log_path",
    "ingested_at_utc",
]


RECOMMENDATION_COLUMNS = [
    "id",
    "run_id",
    "ts_utc",
    "category",
    "campaign_id",
    "target",
    "final_score",
    "business_score",
    "compliance_score",
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
    "ingested_at_utc",
]


def _extract_timestamp_from_filename(path: str) -> Optional[datetime]:
    basename = os.path.basename(path)
    if not basename.startswith("eval_") or not basename.endswith(JSON_EXT):
        return None

    raw = basename.replace("eval_", "").replace(JSON_EXT, "")
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


def _safe_read_json(path: str) -> Optional[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _bool_int(condition: bool) -> int:
    return 1 if condition else 0


def _analysis_row(payload: Dict, path: str, ingested_at: str) -> Dict:
    ts = _extract_timestamp_from_filename(path)
    flags = payload.get("flags", []) or []
    dimensions = payload.get("dimensions", {}) or {}

    return {
        "id": _stable_id(path),
        "run_id": _run_id_from_timestamp(ts),
        "ts_utc": _to_iso_utc(ts),
        "category": payload.get("category", ""),
        "campaign_id": payload.get("campaign_id", ""),
        "target": payload.get("target", ""),
        "analysis_score": payload.get("score", ""),
        "dim_clarity": dimensions.get("clarity", ""),
        "dim_data_grounding": dimensions.get("data_grounding", ""),
        "dim_logic_coherence": dimensions.get("logic_coherence", ""),
        "dim_business_focus": dimensions.get("business_focus", ""),
        "dim_confidence_calibration": dimensions.get("confidence_calibration", ""),
        "dim_no_recommendation": dimensions.get("no_recommendation", ""),
        "flag_count": len(flags),
        "has_low_clarity": _bool_int("low_clarity" in flags),
        "has_low_data_grounding": _bool_int("low_data_grounding" in flags),
        "has_low_logic_coherence": _bool_int("low_logic_coherence" in flags),
        "has_low_business_focus": _bool_int("low_business_focus" in flags),
        "has_low_confidence_calibration": _bool_int(
            "low_confidence_calibration" in flags
        ),
        "has_low_no_recommendation": _bool_int("low_no_recommendation" in flags),
        "has_analysis_contains_recommendations": _bool_int(
            "analysis_contains_recommendations" in flags
        ),
        "has_llm_failed": _bool_int("llm_failed" in flags),
        "raw_log_path": path,
        "ingested_at_utc": ingested_at,
    }


def _recommendation_row(payload: Dict, path: str, ingested_at: str) -> Dict:
    ts = _extract_timestamp_from_filename(path)
    business = payload.get("business", {}) or {}
    compliance = payload.get("compliance", {}) or {}
    ground_truth = payload.get("ground_truth", {}) or {}

    business_flags = business.get("flags", []) or []
    compliance_flags = compliance.get("flags", []) or []
    gt_flags = ground_truth.get("flags", []) or []
    weak = business.get("weak_recommendations", []) or []

    return {
        "id": _stable_id(path),
        "run_id": _run_id_from_timestamp(ts),
        "ts_utc": _to_iso_utc(ts),
        "category": payload.get("category", ""),
        "campaign_id": payload.get("campaign_id", ""),
        "target": payload.get("target", ""),
        "final_score": payload.get("final_score", ""),
        "business_score": business.get("score", ""),
        "compliance_score": compliance.get("score", ""),
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
        ),
        "raw_log_path": path,
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
