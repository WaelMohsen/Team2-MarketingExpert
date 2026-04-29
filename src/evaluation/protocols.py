from typing import Any, Optional, Protocol

from src.schemas.analysis_output_schema import AnalysisOutput


class AnalysisEvaluatorProtocol(Protocol):
    def evaluate(
        self,
        analysis: AnalysisOutput,
        context: str,
        model: Optional[str],
        temp: Optional[float],
    ) -> Any: ...


class RecommendationEvaluatorProtocol(Protocol):
    def evaluate(
        self,
        data: dict,
        model: Optional[str],
        temp: Optional[float],
    ) -> dict: ...


class GroundTruthLoaderProtocol(Protocol):
    def load_ground_truth(self, campaign_id: str, target: str) -> list: ...
