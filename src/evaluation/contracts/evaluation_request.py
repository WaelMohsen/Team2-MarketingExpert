from typing import Any, Dict, List, Union

from pydantic import BaseModel

from src.schemas.analysis_output_schema import AnalysisOutput


class EvaluationRequest(BaseModel):
    model_config = {"frozen": True}

    campaign_id: str
    target: str
    category: str
    campaign_context: str
    analysis_output: Union[AnalysisOutput, Dict[str, Any]]
    recommendation_output: List[Dict[str, Any]]
    kpis: List[Any]
