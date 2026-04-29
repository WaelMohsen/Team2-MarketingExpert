import os
from typing import Any, Dict, List, Optional, Union

from src.evaluation.analysis import AnalysisQualityEvaluator
from src.evaluation.contracts import EvaluationRequest, EvaluationResult
from src.evaluation.recommendation.evaluator import RecommendationEvaluator
from src.evaluation.services import GroundTruthLoader
from src.schemas.analysis_output_schema import AnalysisOutput


class EvaluationOrchestrator:
    """Coordinates evaluation runs while keeping evaluator logic isolated."""

    def __init__(
        self,
        llm_callable,
        embedding_callable,
        analysis_evaluator: Optional[Any] = None,
        recommendation_evaluator: Optional[Any] = None,
        ground_truth_loader: Optional[GroundTruthLoader] = None,
        gt_path: Optional[str] = None,
    ) -> None:
        self.recommendation_evaluator = (
            recommendation_evaluator
            or RecommendationEvaluator(llm=llm_callable, embed=embedding_callable)
        )
        self._analysis_evaluator = analysis_evaluator
        self.ground_truth_loader = ground_truth_loader or GroundTruthLoader()
        self.gt_path = gt_path or os.path.join(
            "data", "benchmark", "recommendation_GT.json"
        )

    @property
    def analysis_evaluator(self) -> AnalysisQualityEvaluator:
        if self._analysis_evaluator is None:
            self._analysis_evaluator = AnalysisQualityEvaluator()
        return self._analysis_evaluator

    def load_ground_truth(
        self,
        path: str,
        campaign_id: str,
        target: str,
    ) -> List[Dict[str, Any]]:
        return self.ground_truth_loader.load(path, campaign_id, target)

    def run_request(
        self,
        request: EvaluationRequest,
        include_analysis: bool = True,
        include_recommendation: bool = True,
    ) -> EvaluationResult:
        analysis_result = None
        recommendation_result = None

        if include_recommendation:
            recommendation_result = self.run_recommendation(
                campaign_id=request.campaign_id,
                target=request.target,
                analysis_output=request.analysis_output,
                recommendation_output=request.recommendation_output,
                kpis=request.kpis,
                category=request.category,
            )

        if include_analysis:
            analysis_result = self.run_analysis(
                analysis_output=request.analysis_output,
                campaign_context=request.campaign_context,
                category=request.category,
                campaign_id=request.campaign_id,
                target=request.target,
            )

        return EvaluationResult(
            campaign_id=request.campaign_id,
            target=request.target,
            category=request.category,
            analysis_result=analysis_result,
            recommendation_result=recommendation_result,
        )

    def run_recommendation(
        self,
        campaign_id: str,
        target: str,
        analysis_output: Union[AnalysisOutput, Dict[str, Any]],
        recommendation_output: List[Dict[str, Any]],
        kpis: List[Any],
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
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
        analysis_output: Union[AnalysisOutput, Dict[str, Any]],
        campaign_context: str = "",
        category: Optional[str] = None,
        campaign_id: Optional[str] = None,
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
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
        analysis_output: Union[AnalysisOutput, Dict[str, Any]],
        recommendation_output: List[Dict[str, Any]],
        kpis: List[Any],
        campaign_context: str = "",
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        request = EvaluationRequest(
            campaign_id=campaign_id,
            target=target,
            category=category,
            campaign_context=campaign_context,
            analysis_output=analysis_output,
            recommendation_output=recommendation_output,
            kpis=kpis,
        )
        return self.run_request(request).to_dict()
