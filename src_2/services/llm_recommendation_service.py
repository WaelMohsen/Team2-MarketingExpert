# services/llm_recommendation_service.py
import json

from schemas.recommendation_output_schema import (
    RecommendationOutput,
    validate_recommendation_output,
)
from services.base_llm_service import BaseLLMService
from services.llm_client import LLMClient
from services.prompt_builder import PromptBuilder


class LLMRecommendationService(BaseLLMService):
    def __init__(self, client: LLMClient, prompt_builder: PromptBuilder):
        self.client = client
        self.prompt_builder = prompt_builder

    def build_system_prompt(self, target):
        system = self.prompt_builder.load("recommendation_prompt.md")
        target_explanation = self.prompt_builder.load_target_prompt(target)
        return f"""
        {system}

        TARGET: {target}
        TARGET EXPLANATION:
        {target_explanation}
        """

    def build_user_prompt(self, target, base_context, selected_metrics, analysis_json=None):
        base_json = json.dumps(base_context.convert_to_dictionary(), ensure_ascii=False)
        metrics_json = json.dumps(selected_metrics.convert_to_dictionary(), ensure_ascii=False)
        analysis_block = f"\nSTEP 1 ANALYSIS:\n{analysis_json}\n" if analysis_json else ""
        return f"""
        You are in Step 2 (Recommendations).

        TARGET: {target}

        BASE CONTEXT:
        {base_json}

        TARGET METRICS:
        {metrics_json}
        {analysis_block}
        Return recommendations JSON only.
        """

    def run(self, target, base_context, selected_metrics, analysis_json=None):

        response = self.client.chat_completion(
            self.build_system_prompt(target),
            self.build_user_prompt(
                target, base_context, selected_metrics, analysis_json
            ),
            RecommendationOutput,
            model="gpt-4o",
        )

        return validate_recommendation_output(
            json.dumps(response.choices[0].message.parsed.dict(), ensure_ascii=False)
        )
