"""Domain models for generated marketing reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..schemas.analysis_output_schema import AnalysisOutput
from ..schemas.recommendation_output_schema import RecommendationCard


@dataclass(frozen=True)
class MarketingReport:
    """Combined analysis and recommendation output for a category."""

    category: str
    analysis: AnalysisOutput
    recommendations: tuple[RecommendationCard, ...]

    def to_response_dict(self) -> dict[str, Any]:
        """Serialize the report into the UI/API response contract."""

        return {
            "analysis": self.analysis.model_dump(),
            "recommendations": [recommendation.model_dump() for recommendation in self.recommendations],
        }
