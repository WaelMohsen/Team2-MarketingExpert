from datetime import datetime
from typing import Callable, Optional

from src.evaluation.recommendation import evaluator
from src.schemas.analysis_output_schema import AnalysisOutput

from .protocols import (
    AnalysisEvaluatorProtocol,
    GroundTruthLoaderProtocol,
    RecommendationEvaluatorProtocol,
)


class EvaluationPipeline:
    """Unified pipeline for evaluation runs.

    Supports recommendation evaluation, analysis evaluation,
    or both in one call.

    ``analysis_evaluator`` is lazy by default: it is only instantiated on
    first call to ``run_analysis``/``run_all``, so recommendation-only paths
    do not require OpenAI credentials.  Pass an explicit instance (or mock)
    to override.
    """

    def __init__(
        self,
        recommendation_evaluator: RecommendationEvaluatorProtocol,
        ground_truth_loader: GroundTruthLoaderProtocol,
        analysis_evaluator: Optional[AnalysisEvaluatorProtocol] = None,
        analysis_evaluator_factory: Optional[
            Callable[[], AnalysisEvaluatorProtocol]
        ] = None,
        timestamp=None,
        analysis_model=None,
        analysis_temp=None,
        recommendation_model=None,
        recommendation_temp=None,
    ):
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.recommendation_evaluator = recommendation_evaluator
        self.ground_truth_loader = ground_truth_loader
        self._analysis_evaluator = analysis_evaluator
        self._analysis_evaluator_factory = analysis_evaluator_factory
        self.timestamp = timestamp
        self.analysis_model = analysis_model
        self.analysis_temp = analysis_temp
        self.recommendation_model = recommendation_model
        self.recommendation_temp = recommendation_temp

    @property
    def analysis_evaluator(self):
        if self._analysis_evaluator is None:
            if self._analysis_evaluator_factory is None:
                raise RuntimeError("No analysis evaluator or factory was provided.")
            self._analysis_evaluator = self._analysis_evaluator_factory()
        return self._analysis_evaluator

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

        gt_data = self.ground_truth_loader.load_ground_truth(campaign_id, target)

        eval_input = {
            "output": recommendation_output,
            "analysis": analysis_payload,
            "kpis": kpis,
            "ground_truth": gt_data,
            "category": category,
            "campaign_id": campaign_id,
            "target": target,
        }

        return self.recommendation_evaluator.evaluate(
            eval_input,
            model=self.recommendation_model,
            temp=self.recommendation_temp,
        )

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
        evaluator = self._analysis_evaluator_factory(target=target)   # fresh, target-bound
        result = evaluator.evaluate(analysis_model, campaign_context, model=self.analysis_model,
            temp=self.analysis_temp)


        if hasattr(result, "model_dump"):
            result = result.model_dump()

        if campaign_id is not None:
            result["campaign_id"] = campaign_id
        if target is not None:
            result["target"] = target
        if category is not None:
            result["category"] = category

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
