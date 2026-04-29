import os

BASE_LOG_DIR = "evaluation_logs"
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
