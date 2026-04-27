import json
import os
from datetime import datetime

from src.llm.client import chat_completion, get_client

from ..schemas.analysis_output_schema import AnalysisOutput, validate_analysis_output
from ..schemas.recommendation_output_schema import (
    RecommendationOutput,
    validate_recommendation_output,
)
from .insight_quality_checker import InsightQualityChecker

from .prompts import (
    analysis_system_prompt,
    build_analysis_user_prompt,
    build_context_block,
    build_recommendation_user_prompt,
    recommendation_system_prompt,
)

CATEGORIES = [
    "Customer Acquisition",
    "Customer Satisfaction",
    "Revenue Growth",
    "Customer Retention",
]

_CATEGORY_PROMPT_FILES = {
    "Customer Acquisition": "customer_acquisition.md",
    "Customer Satisfaction": "customer_satisfaction.md",
    "Revenue Growth": "revenue_growth.md",
    "Customer Retention": "customer_retention.md",
}

OUTPUT_LOG_DIR = "output_log"


def _repo_root_dir() -> str:
    # pipeline.py lives at src/llm/pipeline.py
    this_file = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(this_file)))


def _target_prompt_path_for_category(category: str) -> str:
    prompt_file = _CATEGORY_PROMPT_FILES.get(
        category,
        "response_generation.md",
    )
    return os.path.join(_repo_root_dir(), "prompts", prompt_file)


def save_output(output: dict):
    os.makedirs(OUTPUT_LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_LOG_DIR, f"pipeline_output_{timestamp}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"Output saved to {filename}")

def generate_response(df, category: str, metrics: dict) -> dict: # Changed return type hint to dict
    """Two-step flow: analysis JSON -> recommendation JSON (final schema)."""
    # Initialize a default response structure for consistent returns
    response_data = {
        "kpis": list(metrics.get("overall", {}).keys()),
        "analysis": {},
        "recommendations": [],
        "quality_report": [],
        "status": "ERROR",
        "error_message": None
    }

    try:
        client = get_client()
        target_prompt_path = _target_prompt_path_for_category(category)
        context_block = build_context_block(category, df, metrics)

        # --- Step 1: Analysis ---
        sys_analysis_prompt_path = os.path.join(_repo_root_dir(), "prompts", "system_analysis_prompt.md")
        analysis_sys = analysis_system_prompt(category, target_prompt_path, sys_analysis_prompt_path)
        analysis_user = build_analysis_user_prompt(context_block)
        
        analysis_resp = chat_completion(client, analysis_sys, analysis_user, response_format=AnalysisOutput)
        analysis_model = analysis_resp.choices.message.parsed

        # Custom validators
        analysis_json_str = json.dumps(analysis_model.dict(), ensure_ascii=False)
        analysis_model = validate_analysis_output(analysis_json_str)
        analysis_json_str = json.dumps(analysis_model.dict(), ensure_ascii=False)

        # --- Step 2: Recommendations ---
        rec_prompt_path = os.path.join(_repo_root_dir(), "prompts", "recommendation_system_prompt.md")
        rec_sys = recommendation_system_prompt(category, target_prompt_path, rec_prompt_path)
        rec_user = build_recommendation_user_prompt(context_block, analysis_input=analysis_json_str)
        
        rec_resp = chat_completion(client, rec_sys, rec_user, response_format=RecommendationOutput)
        rec_model = rec_resp.choices.message.parsed

        # Custom validators
        rec_json_str = json.dumps(rec_model.dict(), ensure_ascii=False)
        rec_model = validate_recommendation_output(rec_json_str)

        # --- Step 3: Combine and Quality Check ---
        response_data.update({
            "analysis": analysis_model.dict(),
            "recommendations": [r.dict() for r in rec_model.recommendations],
            "status": "SUCCESS"
        })

        # FIX: Instead of taking the first row, we build a "virtual" row representing the whole campaign
        overall_metrics = dict(metrics.get("overall", {}))
        campaign_row = {}

        # Safely extract frequency (check metrics dict first, then fallback to DataFrame mean)
        if "Average Frequency" in overall_metrics:
            campaign_row["frequency"] = overall_metrics["Average Frequency"]
        elif "frequency" in df.columns:
            campaign_row["frequency"] = df["frequency"].mean()
        else:
            campaign_row["frequency"] = 0

        # Safely extract bounce rate
        if "Average Bounce Rate" in overall_metrics:
            campaign_row["bounce_rate"] = overall_metrics["Average Bounce Rate"]
        elif "bounce_rate" in df.columns:
            campaign_row["bounce_rate"] = df["bounce_rate"].mean()
        else:
            campaign_row["bounce_rate"] = 0

        # Pass any other overall metrics into the row for context
        campaign_row.update(overall_metrics)

        # Now the checker compares AI insights against the ACTUAL averages
        checker = InsightQualityChecker(response_data["analysis"], campaign_row)
        
        results = [
            checker.check_factual_grounding(),
            checker.check_benchmark_specificity(),
            checker.check_issue_detection(),
            checker.check_confidence_calibration(),
        ]

        # Process results and enforce the "Gate"
        report = []
        has_critical_failure = False

        for r in results:
            # Map result to a status
            status = "PASS" if r.passed else ("WARN" if r.partial else "FAIL")
            
            # If a check is not passed and not partial, it's a critical failure
            if status == "FAIL":
                has_critical_failure = True
            
            report.append({
                "name": r.name,
                "status": status,
                "detail": r.detail
            })
            print(f"[{status}] {r.name}: {r.detail}")

        response_data["quality_report"] = report

        # ENFORCE GATE: If critical failure, demote status
        if has_critical_failure:
            response_data["status"] = "REJECTED"
            print("Pipeline Blocked: Quality criteria not met.")

        save_output(response_data)
        return response_data

    except Exception as exc:
        # Standardized error return
        response_data["status"] = "ERROR"
        response_data["error_message"] = str(exc)
        print(f"Pipeline Exception: {exc}")
        return response_data