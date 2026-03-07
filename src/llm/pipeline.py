import os

from .client import chat_completion, get_client
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


def generate_response(df, category: str, metrics: dict) -> str:
    """Two-step flow: analysis JSON -> recommendation JSON (final schema)."""
    try:
        client = get_client()

        target_prompt_path = _target_prompt_path_for_category(category)
        context_block = build_context_block(category, df, metrics)

        analysis_sys = analysis_system_prompt(category, target_prompt_path)
        print("Analysis System Prompt:\n", analysis_sys)  # Debug print
        analysis_user = build_analysis_user_prompt(context_block)
        print("Analysis User Prompt:\n", analysis_user)  # Debug print
        analysis_resp = chat_completion(client, analysis_sys, analysis_user)
        analysis_json_str = analysis_resp.choices[0].message.content

        rec_sys = recommendation_system_prompt(category, target_prompt_path)
        print("Recommendation System Prompt:\n", rec_sys)  # Debug print
        rec_user = build_recommendation_user_prompt(
            context_block,
            analysis_input=analysis_json_str,
        )
        print("Recommendation User Prompt:\n", rec_user)  # Debug print
        rec_resp = chat_completion(client, rec_sys, rec_user)
        return rec_resp.choices[0].message.content
    except Exception as exc:
        return f"Error generating response: {exc}"
