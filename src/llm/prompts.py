from __future__ import annotations

from src.logging.logger import logger


def load_target_prompt(file_path: str) -> str:
    """Load a category target prompt (markdown) and return it as a string."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as exc:
        # Keep behavior simple: return empty prompt rather than crashing.
        logger.error("Error loading target prompt from {}: {}", file_path, exc)
        return ""


def _common_system_instructions(target: str, target_prompt_path: str) -> str:
    target_explanation = load_target_prompt(target_prompt_path)

    return f"""
        Important Note : Take in mind to perform your role based on this marketing campaign target below 
        TARGET: {target}
        TARGET EXPLANATION:
        {target_explanation}

        COMMUNICATION STYLE (STRICT):
        1) Use simple business language.
          2) Avoid abbreviations in final text (do NOT use CTR, ROAS, CPA, CAC,
              LTV, MER). Spell terms out in plain English instead.
        3) Focus on money impact, growth impact, and risk.
        4) Keep each field concise and understandable to a non-marketer.
        5) Think step-by-step internally, but never reveal internal reasoning.
"""


def analysis_system_prompt(target: str, target_prompt_path: str, analysis_prompt_path: str) -> str:
    analysis_prompt=load_target_prompt(analysis_prompt_path)
    return f"""{analysis_prompt}
        {_common_system_instructions(target, target_prompt_path)}       
"""


def recommendation_system_prompt(target: str, target_prompt_path: str, rec_prompt_path: str) -> str:
    rec_prompt = load_target_prompt(rec_prompt_path)
    return f"""{rec_prompt}
        {_common_system_instructions(target, target_prompt_path)}

    """


def build_context_block(category: str, df, metrics: dict) -> str:
    """Build shared business-first context.

    No schemas, and no step instructions.
    """
    campaign_raw_data=df.to_dict("records")
    metrics_overall= metrics.get('overall')
    metrics_per_channel=metrics.get('per_channel')

    return f"""
        BUSINESS:
        (Infer business type from campaign data)
        Goal: {category}

        CAMPAIGN RAW DATA:
        {campaign_raw_data}

        PLAIN BUSINESS METRICS:
         - Across all channels (overall)
            {metrics_overall}
         - per_channel
            {metrics_per_channel}

        IMPORTANT:
        - Write for a business lead with no marketing background.
        - Keep wording simple and practical.
        - Avoid abbreviations in the final JSON text.
    """


def build_analysis_user_prompt(context_block: str) -> str:
    return f"""
        You are in Step 1 (Analysis Only).

        Use the context below and return analysis JSON only.

        CONTEXT:
        {context_block}
    """


def build_recommendation_user_prompt(
    context_block: str,
    analysis_input: str,
) -> str:
    return f"""
        You are in Step 2 (Recommendation).

        Use the context below PLUS the Step 1 analysis JSON
        to produce the final report JSON.

        CONTEXT:
        {context_block}

        STEP 1 ANALYSIS JSON (input):
        {analysis_input}
    """
