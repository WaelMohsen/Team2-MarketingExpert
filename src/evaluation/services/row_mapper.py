import uuid
from typing import Dict

from .log_reader import extract_timestamp_from_filename


def _bool_int(condition: bool) -> int:
    return 1 if condition else 0


def _to_iso_utc(dt) -> str:
    if dt is None:
        return ""
    return dt.isoformat() + "Z"


def _run_id_from_timestamp(dt) -> str:
    if dt is None:
        return ""
    return dt.strftime("run_%Y%m%d_%H%M%S")


def analysis_row(payload: Dict, path: str, ingested_at: str) -> Dict:
    ts = extract_timestamp_from_filename(path)
    flags = payload.get("flags", []) or []
    dimensions = payload.get("dimensions", {}) or {}

    return {
        "id": str(uuid.uuid4()),
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


def recommendation_row(payload: Dict, path: str, ingested_at: str) -> Dict:
    ts = extract_timestamp_from_filename(path)
    business = payload.get("business", {}) or {}
    compliance = payload.get("compliance", {}) or {}
    ground_truth = payload.get("ground_truth", {}) or {}

    business_flags = business.get("flags", []) or []
    compliance_flags = compliance.get("flags", []) or []
    gt_flags = ground_truth.get("flags", []) or []
    weak = business.get("weak_recommendations", []) or []

    return {
        "id": str(uuid.uuid4()),
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
