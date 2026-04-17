# services/llm_analysis_service.py
import json

from schemas.analysis_output_schema import AnalysisOutput, validate_analysis_output
from services.base_llm_service import BaseLLMService
from services.llm_client import LLMClient
from services.prompt_builder import PromptBuilder


class LLMAnalysisService(BaseLLMService):
    def __init__(self, client: LLMClient, prompt_builder: PromptBuilder):
        self.client = client
        self.prompt_builder = prompt_builder

    def build_system_prompt(self, target):
        system = self.prompt_builder.load("analysis_prompt.md")
        target_explanation = self.prompt_builder.load_target_prompt(target)
        return f"""
        {system}

        TARGET: {target}
        TARGET EXPLANATION:
        {target_explanation}
        """

    def build_user_prompt(
        self, target, base_context, selected_metrics, analysis_json=None
    ):
        return f"""
        You are in Step 1 (Analysis Only).

        TARGET: {target}

        BASE CONTEXT:
        {base_context}

        TARGET METRICS:
        {selected_metrics}

        Return analysis JSON only.
        """

    def run(self, target, base_context, selected_metrics, analysis_json=None):

        response = self.client.chat_completion(
            self.build_system_prompt(target),
            self.build_user_prompt(target, base_context, selected_metrics),
            AnalysisOutput,
            model="gpt-4o-mini",
        )

        model = validate_analysis_output(
            json.dumps(response.choices[0].message.parsed.dict(), ensure_ascii=False)
        )

        return {"model": model, "json": json.dumps(model.dict(), ensure_ascii=False)}
