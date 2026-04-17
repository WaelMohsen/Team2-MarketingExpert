# services/llm_orchestrator.py
import json
import os
from datetime import datetime

from services.llm_analysis_service import LLMAnalysisService
from services.llm_client import LLMClient
from services.llm_recommendation_service import LLMRecommendationService
from services.prompt_builder import PromptBuilder


class LLMOrchestrator:
    def __init__(self, prompts_dir="prompts", output_log_dir="output_log"):
        client = LLMClient()
        prompt_builder = PromptBuilder(prompts_dir)
        self.analysis = LLMAnalysisService(client, prompt_builder)
        self.recommendation = LLMRecommendationService(client, prompt_builder)
        self.output_log_dir = output_log_dir

    def run(self, target, metrics, selected_metrics):
        # step 1 — analysis
        analysis = self.analysis.run(target, metrics, selected_metrics)

        # step 2 — recommendation receives step 1 output
        recommendations = self.recommendation.run(
            target, metrics, selected_metrics, analysis["json"]
        )

        combined = {
            "analysis": analysis["model"].dict(),
            "recommendations": [r.dict() for r in recommendations.recommendations],
        }

        self._save_output(combined)
        return combined

    def _save_output(self, output):
        os.makedirs(self.output_log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_log_dir, f"output_{timestamp}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4, ensure_ascii=False)
        print(f"Output saved to {filename}")
