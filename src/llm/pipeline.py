import os
import json
from datetime import datetime

from src.llm.client import chat_completion, get_client
from ..schemas.analysis_output_schema import AnalysisOutput
from ..schemas.analysis_output_schema import validate_analysis_output
from ..schemas.recommendation_output_schema import RecommendationOutput
from ..schemas.recommendation_output_schema import validate_recommendation_output
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


def generate_response(df, category: str, metrics: dict) -> str:
    """Two-step flow: analysis JSON -> recommendation JSON (final schema)."""
    try:
        client = get_client()

        target_prompt_path = _target_prompt_path_for_category(category)
        context_block = build_context_block(category, df, metrics)

        sys_analysis_prompt_path = os.path.join(_repo_root_dir(), "prompts", "system_analysis_prompt.md")
        analysis_sys = analysis_system_prompt(category, target_prompt_path, sys_analysis_prompt_path)
        print("Analysis System Prompt:\n", analysis_sys)  # Debug print
        analysis_user = build_analysis_user_prompt(context_block)
        print("Analysis User Prompt:\n", analysis_user)  # Debug print
        analysis_resp = chat_completion(
            client,
            analysis_sys,
            analysis_user,
            response_format=AnalysisOutput,
        )
        # SDK parses the response into a Pydantic instance automatically.
        analysis_model = analysis_resp.choices[0].message.parsed

        # Run our custom validators (confidence normalization, empty-field checks).
        analysis_json_str = json.dumps(analysis_model.dict(), ensure_ascii=False)
        analysis_model = validate_analysis_output(analysis_json_str)
        analysis_json_str = json.dumps(analysis_model.dict(), ensure_ascii=False)

        rec_prompt_path = os.path.join(_repo_root_dir(), "prompts", "recommendation_system_prompt.md")
        rec_sys = recommendation_system_prompt(category, target_prompt_path, rec_prompt_path)
        print("Recommendation System Prompt:\n", rec_sys)  # Debug print
        rec_user = build_recommendation_user_prompt(
            context_block,
            analysis_input=analysis_json_str,
        )
        print("Recommendation User Prompt:\n", rec_user)  # Debug print
        rec_resp = chat_completion(
            client,
            rec_sys,
            rec_user,
            response_format=RecommendationOutput,
        )
        rec_model = rec_resp.choices[0].message.parsed
        print("Final Recommendation parsed:", rec_model)  # Debug print

        # Run our custom validators (count check, empty-field checks).
        rec_json_str = json.dumps(rec_model.dict(), ensure_ascii=False)
        rec_model = validate_recommendation_output(rec_json_str)

        # Combine both steps into a single response for the UI.
        combined = {
            "analysis": analysis_model.dict(),
            "recommendations": [r.dict() for r in rec_model.recommendations],
        }

        combined_json = json.dumps(combined, ensure_ascii=False)
        save_output(combined)  # Save the full response for debugging
        return combined_json
    except Exception as exc:
        return f"Error generating response: {exc}"
