import json
import os

from src.evaluation.analysis_quality_evaluator import AnalysisQualityEvaluator
from src.evaluation.recommendation.evaluator import RecommendationEvaluator
from src.schemas.analysis_output_schema import AnalysisOutput


class EvaluationPipeline:
    """Unified pipeline for evaluation runs.

    Supports recommendation evaluation, analysis evaluation,
    or both in one call.
    """

    def __init__(self, llm_callable, embedding_callable):
        self.recommendation_evaluator = RecommendationEvaluator(
            llm=llm_callable, embed=embedding_callable
        )
        self.analysis_evaluator = AnalysisQualityEvaluator()
        self.gt_path = os.path.join("data", "benchmark", "recommendation_GT.json")

    def load_ground_truth(self, path, campaign_id, target):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for campaign in data:
            if campaign["campaign_id"] == campaign_id:
                return campaign["ground_truth"].get(target, [])

        return []

    def run_recommendation(
        self,
        campaign_id: str,
        target: str,
        analysis_output,
        recommendation_output: list,
        kpis: list,
        category=None,
    ):
        if isinstance(analysis_output, AnalysisOutput):
            analysis_payload = analysis_output.model_dump()
        else:
            analysis_payload = analysis_output

        gt_data = self.load_ground_truth(self.gt_path, campaign_id, target)

        eval_input = {
            "output": recommendation_output,
            "analysis": analysis_payload,
            "kpis": kpis,
            "ground_truth": gt_data,
            "category": category,
        }

        return self.recommendation_evaluator.evaluate(eval_input)

    def run_analysis(
        self,
        analysis_output,
        campaign_context: str = "",
        category=None,
    ):
        if isinstance(analysis_output, AnalysisOutput):
            analysis_model = analysis_output
        else:
            analysis_model = AnalysisOutput(**analysis_output)

        return self.analysis_evaluator.evaluate(
            analysis_model, campaign_context, category=category
        )

    def run_all(
        self,
        campaign_id: str,
        target: str,
        analysis_output,
        recommendation_output: list,
        kpis: list,
        campaign_context: str = "",
        category=None,
    ):
        recommendation_result = self.run_recommendation(
            campaign_id=campaign_id,
            target=target,
            analysis_output=analysis_output,
            recommendation_output=recommendation_output,
            kpis=kpis,
            category=category,
        )
        analysis_result = self.run_analysis(
            analysis_output=analysis_output,
            campaign_context=campaign_context,
            category=category,
        )

        return {
            "recommendation_evaluation": recommendation_result,
            "analysis_evaluation": analysis_result,
        }
