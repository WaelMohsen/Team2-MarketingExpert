import json
import os

from src.evaluation.analysis_quality_evaluator import AnalysisQualityEvaluator
from src.evaluation.recommendation.evaluator import RecommendationEvaluator
from src.schemas.analysis_output_schema import AnalysisOutput


class EvaluationPipeline:
    """Unified pipeline for evaluation runs.

    Supports recommendation evaluation, analysis evaluation,
    or both in one call.

    ``analysis_evaluator`` is lazy by default: it is only instantiated on
    first call to ``run_analysis``/``run_all``, so recommendation-only paths
    do not require OpenAI credentials.  Pass an explicit instance (or mock)
    to override.
    """

    def __init__(self, llm_callable, embedding_callable, analysis_evaluator=None):
        self.recommendation_evaluator = RecommendationEvaluator(
            llm=llm_callable, embed=embedding_callable
        )
        self._analysis_evaluator = analysis_evaluator
        self.gt_path = os.path.join("data", "benchmark", "recommendation_GT.json")

    @property
    def analysis_evaluator(self):
        if self._analysis_evaluator is None:
            self._analysis_evaluator = AnalysisQualityEvaluator()
        return self._analysis_evaluator

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
            "campaign_id": campaign_id,
            "target": target,
        }

        return self.recommendation_evaluator.evaluate(eval_input)

    def run_analysis(
        self,
        analysis_output,
        campaign_context: str = "",
        category=None,
        campaign_id=None,
        target=None,
    ):
        if isinstance(analysis_output, AnalysisOutput):
            analysis_model = analysis_output
        else:
            analysis_model = AnalysisOutput(**analysis_output)

        result = self.analysis_evaluator.evaluate(
            analysis_model, campaign_context, category=category
        )

        if campaign_id is not None:
            result["campaign_id"] = campaign_id
        if target is not None:
            result["target"] = target

        return result

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
            campaign_id=campaign_id,
            target=target,
        )

        return {
            "recommendation_evaluation": recommendation_result,
            "analysis_evaluation": analysis_result,
        }
