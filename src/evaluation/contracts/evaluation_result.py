from typing import Any, Dict, Optional

from pydantic import BaseModel


class EvaluationResult(BaseModel):
    model_config = {"frozen": True}

    campaign_id: str
    target: str
    category: Optional[str] = None
    analysis_result: Optional[Dict[str, Any]] = None
    recommendation_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "target": self.target,
            "category": self.category,
            "analysis_evaluation": self.analysis_result,
            "recommendation_evaluation": self.recommendation_result,
        }
