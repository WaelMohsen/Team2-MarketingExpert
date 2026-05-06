import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from src.llm.client import chat_completion, get_client

from ..schemas.analysis_output_schema import (
    AnalysisOutput,
    get_analysis_schema,
    validate_analysis_output,
)
from ..schemas.recommendation_output_schema import (
    RecommendationOutput,
    validate_recommendation_output,
)
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


def _resolve_generation_settings(
    analysis_model: Optional[str],
    analysis_temp: Optional[float],
    recommendation_model: Optional[str],
    recommendation_temp: Optional[float],
) -> Tuple[str, float, str, float]:
    from src.evaluation.run_config import load_run_config

    if None not in (
        analysis_model,
        analysis_temp,
        recommendation_model,
        recommendation_temp,
    ):
        return (
            analysis_model,
            analysis_temp,
            recommendation_model,
            recommendation_temp,
        )

    generation = load_run_config().generation
    return (
        analysis_model or generation.analysis_model,
        generation.analysis_temp if analysis_temp is None else analysis_temp,
        recommendation_model or generation.recommendation_model,
        (
            generation.recommendation_temp
            if recommendation_temp is None
            else recommendation_temp
        ),
    )


def generate_response(
    df,
    category: str,
    metrics: dict,
    Analysis_model: Optional[str] = None,
    Analysis_temp: Optional[float] = None,
    Rec_model: Optional[str] = None,
    Rec_temp: Optional[float] = None,
) -> Dict[str, Any]:
    """Two-step flow: analysis JSON -> recommendation JSON (final schema)."""
    (
        analysis_model_name,
        analysis_temperature,
        recommendation_model_name,
        recommendation_temperature,
    ) = _resolve_generation_settings(
        Analysis_model,
        Analysis_temp,
        Rec_model,
        Rec_temp,
    )

    client = get_client()

    target_prompt_path = _target_prompt_path_for_category(category)
    context_block = build_context_block(category, df, metrics)

    sys_analysis_prompt_path = os.path.join(
        _repo_root_dir(), "prompts", "system_analysis_prompt.md"
    )
    analysis_sys = analysis_system_prompt(
        category, target_prompt_path, sys_analysis_prompt_path
    )
    analysis_user = build_analysis_user_prompt(context_block)
    analysis_schema = get_analysis_schema(category)
    analysis_resp = chat_completion(
        client,
        analysis_sys,
        analysis_user,
        response_format=analysis_schema,
        model=analysis_model_name,
        temp=analysis_temperature,
    )
    # SDK parses the response into a Pydantic instance automatically.
    analysis_model = analysis_resp.choices[0].message.parsed

    # Run our custom validators (confidence normalization, empty-field checks).
    analysis_json_str = json.dumps(analysis_model.model_dump(), ensure_ascii=False)
    analysis_model = validate_analysis_output(analysis_json_str, category)
    analysis_json_str = json.dumps(analysis_model.model_dump(), ensure_ascii=False)

    rec_prompt_path = os.path.join(
        _repo_root_dir(), "prompts", "recommendation_system_prompt.md"
    )
    rec_sys = recommendation_system_prompt(
        category, target_prompt_path, rec_prompt_path
    )
    rec_user = build_recommendation_user_prompt(
        context_block,
        analysis_input=analysis_json_str,
    )
    rec_resp = chat_completion(
        client,
        rec_sys,
        rec_user,
        response_format=RecommendationOutput,
        model=recommendation_model_name,
        temp=recommendation_temperature,
    )
    rec_model = rec_resp.choices[0].message.parsed

    # Run our custom validators (count check, empty-field checks).
    rec_json_str = json.dumps(rec_model.model_dump(), ensure_ascii=False)
    rec_model = validate_recommendation_output(rec_json_str)

    # Combine both steps into a single response for the UI.
    combined = {
        "Target": category,
        "metrics": metrics,
        "kpis": list(metrics.get("overall", {}).keys()),
        "analysis": analysis_model.model_dump(),
        "recommendations": [
            recommendation.model_dump() for recommendation in rec_model.recommendations
        ],
    }

    save_output(combined)  # Save the full response for debugging
    return combined
